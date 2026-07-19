"""Portable launcher for running the Streamlit app with port fallback."""

from __future__ import annotations

import atexit
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Iterable
from urllib import error as urllib_error
from urllib import request as urllib_request

APP_NAME = "MyFinModel"
PREFERRED_PORT = 8501
MAX_PORT = 8510
FALLBACK_PORTS = range(8502, MAX_PORT + 1)
STARTUP_TIMEOUT_SECONDS = 20
POLL_INTERVAL_SECONDS = 0.25
LOCALHOST = "127.0.0.1"
STREAMLIT_HEALTH_PATH = "/_stcore/health"
ACTIVE_PORT_FILE_NAME = "active-port.txt"
HTTP_PROBE_BODY_BYTES = 256
HTTP_PROBE_TIMEOUT_SECONDS = 1


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

            body = (
                response.read(HTTP_PROBE_BODY_BYTES)
                .decode("utf-8", errors="ignore")
                .strip()
            )
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


def _find_existing_instance_port(timeout_seconds: int) -> int | None:
    active_port = _read_active_port()
    if active_port is not None:
        if _wait_for_streamlit_ready(active_port, timeout_seconds):
            return active_port
        if _is_port_available(active_port):
            _clear_active_port(active_port)

    for port in _iterate_candidate_ports():
        if not _is_port_available(port) and _is_streamlit_ready(port):
            return port
    return None


def _open_browser(port: int, logger: logging.Logger) -> None:
    url = f"http://{LOCALHOST}:{port}"
    logger.info("Opening browser at %s", url)
    try:
        webbrowser.open(url)
    except Exception as exc:
        logger.exception("Failed to open browser: %s", exc)


def _wait_and_open_browser(port: int, logger: logging.Logger, notify_user=None) -> None:
    if not _wait_for_streamlit_ready(port, STARTUP_TIMEOUT_SECONDS):
        logger.error("Streamlit did not start within timeout (%ds).", STARTUP_TIMEOUT_SECONDS)
        if notify_user:
            notify_user(f"{APP_NAME} failed to start. See launcher log for details.")
        return
    _write_active_port(port)
    _open_browser(port, logger)


def _run_streamlit(app_path: str, port: int) -> None:
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = LOCALHOST
    os.environ["STREAMLIT_SERVER_BASE_URL_PATH"] = ""
    os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    import streamlit.web.bootstrap as bootstrap
    from streamlit import config as _config

    _config.set_option("server.headless", True)
    _config.set_option("browser.gatherUsageStats", False)
    _config.set_option("server.port", port)
    _config.set_option("server.address", LOCALHOST)
    _config.set_option("server.baseUrlPath", "")
    _config.set_option("server.runOnSave", False)
    _config.set_option("server.fileWatcherType", "none")
    _config.set_option("global.developmentMode", False)

    bootstrap.run(app_path, False, [], {})


def main() -> int:
    logger = _configure_logger()

    def _notify_user(message: str) -> None:
        """Best-effort user-visible error for windowless launcher builds."""
        try:
            import ctypes  # type: ignore[attr-defined]

            ctypes.windll.user32.MessageBoxW(0, message, APP_NAME, 0x10)
        except Exception:
            print(message)

    try:
        existing_port = _find_existing_instance_port(STARTUP_TIMEOUT_SECONDS)
        if existing_port is not None:
            logger.info("Reusing running launcher instance on port %s", existing_port)
            _write_active_port(existing_port)
            _open_browser(existing_port, logger)
            return 0

        app_path = _resolve_app_path()
        port = _select_port()
        _write_active_port(port)
        atexit.register(_clear_active_port, port)
        logger.info("Selected local port: %s", port)
    except Exception as exc:
        logger.exception("Failed during launcher setup: %s", exc)
        _notify_user(f"{APP_NAME} failed to start: {exc}")
        return 1

    try:
        browser_thread = threading.Thread(
            target=_wait_and_open_browser,
            args=(port, logger, _notify_user),
            daemon=True,
        )
        browser_thread.start()
        _run_streamlit(str(app_path), port)
    except Exception as exc:
        _clear_active_port(port)
        logger.exception("Failed to start Streamlit: %s", exc)
        _notify_user(f"{APP_NAME} failed to start: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
