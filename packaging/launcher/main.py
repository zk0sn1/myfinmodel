"""Portable launcher for running the Streamlit app with port fallback."""

from __future__ import annotations

import atexit
import contextlib
import logging
import multiprocessing
import os
import socket
import sys
import threading
import time
import subprocess
import webbrowser
from pathlib import Path
from typing import Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib import error as urllib_error
from urllib import request as urllib_request

APP_NAME = "MyFinModel"
PREFERRED_PORT = 8501
# Match the current Streamlit 1.58 built-in port search window so the launcher
# can detect the actual fallback port that the bundled server ends up using.
STREAMLIT_PORT_SEARCH_RETRIES = 100
MAX_PORT = PREFERRED_PORT + STREAMLIT_PORT_SEARCH_RETRIES
FALLBACK_PORTS = range(8502, MAX_PORT + 1)
# Frozen Streamlit startup imports a large scientific stack; portable launches
# have already been observed taking ~15 seconds, so use a 45-second window
# (roughly 3x that startup time) to leave headroom on slower Windows systems
# before showing a failure dialog.
STARTUP_TIMEOUT_SECONDS = 45
EXISTING_INSTANCE_PROBE_SECONDS = 3
LOCK_ACQUISITION_RETRIES = 3
POLL_INTERVAL_SECONDS = 0.25
LOCALHOST = "127.0.0.1"
STREAMLIT_HEALTH_PATH = "/_stcore/health"
ACTIVE_PORT_FILE_NAME = "active-port.txt"
STARTUP_LOCK_FILE_NAME = "launcher-starting.lock"
HTTP_PROBE_TIMEOUT_SECONDS = 1
SHUTDOWN_BEACON_PATH = "/shutdown"
SHUTDOWN_CONTROL_PORT_ENV = "MYFINMODEL_SHUTDOWN_CONTROL_PORT"
SHUTDOWN_CONTROL_TOKEN_ENV = "MYFINMODEL_SHUTDOWN_TOKEN"


class LauncherState:
    def __init__(self) -> None:
        self.started_port: int | None = None
        self.owns_startup_lock = False
        self.cleaned_up = False
        self.shutdown_server: ThreadingHTTPServer | None = None
        self.shutdown_server_thread: threading.Thread | None = None


class _ShutdownRequestHandler(BaseHTTPRequestHandler):
    server_version = "MyFinModelShutdown/1.0"

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        expected_path = f"{SHUTDOWN_BEACON_PATH}/{getattr(self.server, 'shutdown_token', '')}"
        parsed = urlparse(self.path)
        if parsed.path != expected_path:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(204)
        self.end_headers()

        threading.Thread(target=_terminate_launcher_tree, daemon=True).start()

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - stdlib API
        return


def _terminate_launcher_tree() -> None:
    with contextlib.suppress(Exception):
        subprocess.run(
            ["taskkill", "/PID", str(os.getpid()), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )


def _logs_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME / "logs"
    return Path.home() / "AppData" / "Local" / APP_NAME / "logs"


def _configure_logger() -> logging.Logger:
    log_dir = _logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("myfinmodel.launcher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_dir / "launcher.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def _start_shutdown_control_server(logger: logging.Logger, state: LauncherState) -> tuple[int, str]:
    token = os.urandom(16).hex()
    server = ThreadingHTTPServer((LOCALHOST, 0), _ShutdownRequestHandler)
    server.shutdown_token = token  # type: ignore[attr-defined]
    server.daemon_threads = True
    server.allow_reuse_address = True

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    state.shutdown_server = server
    state.shutdown_server_thread = thread

    logger.info("Shutdown control server listening on port %s", server.server_address[1])
    return int(server.server_address[1]), token


def _stop_shutdown_control_server(state: LauncherState) -> None:
    if state.shutdown_server is None:
        return
    with contextlib.suppress(Exception):
        state.shutdown_server.shutdown()
        state.shutdown_server.server_close()
    state.shutdown_server = None
    state.shutdown_server_thread = None


def _iterate_candidate_ports() -> Iterable[int]:
    yield PREFERRED_PORT
    yield from FALLBACK_PORTS


def _is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((LOCALHOST, port)) != 0


def _select_port() -> int:
    for port in _iterate_candidate_ports():
        if _is_port_available(port):
            return port
    raise RuntimeError(
        f"No available local port found from {PREFERRED_PORT} through {MAX_PORT}."
    )


def _repository_root() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller one-dir uses _MEIPASS; fallback to executable folder when unavailable.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def _resolve_app_path() -> Path:
    app_path = _repository_root() / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"Could not find Streamlit entrypoint: {app_path}")
    return app_path


def _active_port_file() -> Path:
    return _logs_dir() / ACTIVE_PORT_FILE_NAME


def _startup_lock_file() -> Path:
    return _logs_dir() / STARTUP_LOCK_FILE_NAME


def _read_active_port() -> int | None:
    try:
        raw_value = _active_port_file().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None

    try:
        port = int(raw_value)
    except ValueError:
        return None

    if PREFERRED_PORT <= port <= MAX_PORT:
        return port
    return None


def _write_active_port(port: int) -> None:
    _active_port_file().parent.mkdir(parents=True, exist_ok=True)
    _active_port_file().write_text(str(port), encoding="utf-8")


def _acquire_startup_lock(timeout_seconds: int) -> bool:
    """Acquire the startup lock for this launcher process.

    Returns True when this process created the lock file. Returns False when
    another process still holds a non-stale lock. The timeout is used only to
    decide when an existing lock is stale enough to delete and retry.
    """
    startup_lock_file = _startup_lock_file()
    startup_lock_file.parent.mkdir(parents=True, exist_ok=True)

    # A few retries are enough here because the only expected race is another
    # process deleting a stale lock between our existence check and unlink.
    for _ in range(LOCK_ACQUISITION_RETRIES):
        try:
            # O_CREAT | O_EXCL makes lock creation atomic across processes.
            fd = os.open(startup_lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age_seconds = time.time() - startup_lock_file.stat().st_mtime
            except FileNotFoundError:
                continue

            if age_seconds > timeout_seconds:
                try:
                    startup_lock_file.unlink()
                except FileNotFoundError:
                    pass
                continue
            return False

        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
            return True
        finally:
            os.close(fd)

    return False


def _release_startup_lock() -> None:
    try:
        _startup_lock_file().unlink()
    except FileNotFoundError:
        pass


def _clear_active_port(expected_port: int | None = None) -> None:
    active_port_file = _active_port_file()
    if not active_port_file.exists():
        return

    if expected_port is not None and _read_active_port() != expected_port:
        return

    try:
        active_port_file.unlink()
    except FileNotFoundError:
        pass


def _http_ok(
    url: str,
    *,
    expected_body: str | None = None,
    expected_content_type: str | None = None,
) -> bool:
    try:
        with urllib_request.urlopen(url, timeout=HTTP_PROBE_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                return False

            if expected_content_type and (
                response.headers.get_content_type() != expected_content_type
            ):
                return False

            if expected_body is None:
                return True

            body = response.read().decode("utf-8", errors="ignore").strip()
            return body == expected_body
    except (OSError, ValueError, urllib_error.URLError):
        return False


def _is_streamlit_ready(port: int) -> bool:
    base_url = f"http://{LOCALHOST}:{port}"
    if not _http_ok(
        f"{base_url}{STREAMLIT_HEALTH_PATH}",
        expected_body="ok",
    ):
        return False
    return _http_ok(base_url, expected_content_type="text/html")


def _wait_for_streamlit_ready(port: int, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _is_streamlit_ready(port):
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def _find_ready_streamlit_port() -> int | None:
    for port in _iterate_candidate_ports():
        if not _is_port_available(port) and _is_streamlit_ready(port):
            return port
    return None


def _wait_for_new_streamlit_port(timeout_seconds: int) -> int | None:
    """Poll until any ready Streamlit instance is detected on candidate ports."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        ready_port = _find_ready_streamlit_port()
        if ready_port is not None:
            return ready_port
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


def _find_existing_instance_port(timeout_seconds: int) -> int | None:
    active_port = _read_active_port()
    if active_port is not None:
        # Fast-path stale marker cleanup: if no listener owns the recorded port,
        # do not spend full startup timeout waiting on a dead prior instance.
        if _is_port_available(active_port):
            _clear_active_port(active_port)
            return None

        # Short probe only. A long wait here causes very slow launcher startup
        # when prior runs left stale process/lock state.
        probe_timeout = min(timeout_seconds, EXISTING_INSTANCE_PROBE_SECONDS)
        if _wait_for_streamlit_ready(active_port, probe_timeout):
            return active_port
        if _is_port_available(active_port):
            _clear_active_port(active_port)
        return None

    # Avoid scanning all fallback ports during initial startup; this can add
    # substantial latency and is only needed when coordinating with another
    # launcher process or after we've started Streamlit ourselves.
    return None


def _open_browser(port: int, logger: logging.Logger) -> None:
    url = f"http://{LOCALHOST}:{port}"
    logger.info("Opening browser at %s", url)
    try:
        webbrowser.open(url)
    except Exception as exc:
        logger.exception("Failed to open browser: %s", exc)


def _streamlit_runtime_settings(port: int) -> tuple[dict[str, str], dict[str, object]]:
    option_values: dict[str, object] = {
        "server.headless": True,
        "browser.gatherUsageStats": False,
        "server.port": port,
        "server.address": LOCALHOST,
        "server.baseUrlPath": "",
        "server.runOnSave": False,
        "server.fileWatcherType": "none",
        "global.developmentMode": False,
    }
    env_values = {
        "STREAMLIT_SERVER_HEADLESS": "true",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "STREAMLIT_SERVER_PORT": str(port),
        "STREAMLIT_SERVER_ADDRESS": LOCALHOST,
        "STREAMLIT_SERVER_BASE_URL_PATH": "",
        "STREAMLIT_SERVER_RUN_ON_SAVE": "false",
        "STREAMLIT_SERVER_FILE_WATCHER_TYPE": "none",
        "STREAMLIT_GLOBAL_DEVELOPMENT_MODE": "false",
    }
    return env_values, option_values


def _wait_and_open_browser(
    logger: logging.Logger,
    state: LauncherState,
    selected_port: int,
    notify_user=None,
) -> None:
    start_time = time.perf_counter()

    # First probe the explicitly selected port to avoid scanning 100+ ports
    # during normal startup.
    port: int | None
    if _wait_for_streamlit_ready(selected_port, STARTUP_TIMEOUT_SECONDS):
        port = selected_port
    else:
        logger.info(
            "Selected port %s did not become ready in %ss; scanning fallback range.",
            selected_port,
            STARTUP_TIMEOUT_SECONDS,
        )
        port = _wait_for_new_streamlit_port(STARTUP_TIMEOUT_SECONDS)

    if port is None:
        _release_startup_lock()
        state.owns_startup_lock = False
        logger.error("Streamlit did not start within timeout (%ds).", STARTUP_TIMEOUT_SECONDS)
        if notify_user:
            notify_user(f"{APP_NAME} failed to start. See launcher log for details.")
        return

    elapsed = time.perf_counter() - start_time
    logger.info("Streamlit became ready on port %s in %.2fs", port, elapsed)

    _write_active_port(port)
    state.started_port = port
    _release_startup_lock()
    state.owns_startup_lock = False
    _open_browser(port, logger)


def _run_streamlit(app_path: str, port: int) -> None:
    env_values, option_values = _streamlit_runtime_settings(port)
    os.environ.update(env_values)

    import streamlit.web.bootstrap as bootstrap
    from streamlit import config as _config

    for option_name, option_value in option_values.items():
        _config.set_option(option_name, option_value)

    bootstrap.run(app_path, False, [], {})


def main() -> int:
    # Required for PyInstaller + multiprocessing on Windows. Without this,
    # child helper processes can re-run launcher startup logic unexpectedly.
    multiprocessing.freeze_support()

    logger = _configure_logger()
    state = LauncherState()
    selected_port: int | None = None

    def _notify_user(message: str) -> None:
        """Best-effort user-visible error for windowless launcher builds."""
        try:
            import ctypes  # type: ignore[attr-defined]

            ctypes.windll.user32.MessageBoxW(0, message, APP_NAME, 0x10)
        except Exception:
            print(message)

    def _cleanup_launcher_state() -> None:
        if state.cleaned_up:
            return
        state.cleaned_up = True
        if state.started_port is not None:
            _clear_active_port(state.started_port)
        if state.owns_startup_lock:
            _release_startup_lock()
            state.owns_startup_lock = False
            _stop_shutdown_control_server(state)

    try:
        logger.info("Launcher startup initiated.")
        startup_t0 = time.perf_counter()
        shutdown_control_port, shutdown_token = _start_shutdown_control_server(logger, state)
        os.environ[SHUTDOWN_CONTROL_PORT_ENV] = str(shutdown_control_port)
        os.environ[SHUTDOWN_CONTROL_TOKEN_ENV] = shutdown_token
        existing_port = _find_existing_instance_port(STARTUP_TIMEOUT_SECONDS)
        logger.info(
            "Existing-instance probe completed in %.2fs",
            time.perf_counter() - startup_t0,
        )
        if existing_port is not None:
            logger.info("Reusing running launcher instance on port %s", existing_port)
            _write_active_port(existing_port)
            _open_browser(existing_port, logger)
            return 0

        if not _acquire_startup_lock(STARTUP_TIMEOUT_SECONDS):
            logger.info("Another launcher is starting; waiting for the ready app instance.")
            existing_port = _find_existing_instance_port(STARTUP_TIMEOUT_SECONDS)
            if existing_port is not None:
                logger.info("Reusing newly started launcher instance on port %s", existing_port)
                _write_active_port(existing_port)
                _open_browser(existing_port, logger)
                return 0
            raise RuntimeError(
                f"{APP_NAME} did not finish starting within {STARTUP_TIMEOUT_SECONDS} seconds. "
                f"Check {_logs_dir() / 'launcher.log'} and try again."
            )

        state.owns_startup_lock = True
        atexit.register(_cleanup_launcher_state)
        selected_port = _select_port()
        logger.info("Selected local port: %s", selected_port)
        app_path = _resolve_app_path()
    except Exception as exc:
        _cleanup_launcher_state()
        logger.exception("Failed during launcher setup: %s", exc)
        _notify_user(f"{APP_NAME} failed to start: {exc}")
        return 1

    try:
        browser_thread = threading.Thread(
            target=_wait_and_open_browser,
            args=(logger, state, selected_port if selected_port is not None else PREFERRED_PORT, _notify_user),
            daemon=True,
        )
        browser_thread.start()
        _run_streamlit(
            str(app_path),
            selected_port if selected_port is not None else PREFERRED_PORT,
        )
    except Exception as exc:
        _cleanup_launcher_state()
        logger.exception("Failed to start Streamlit: %s", exc)
        _notify_user(f"{APP_NAME} failed to start: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
