from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType


def _load_launcher_module():
    module_path = Path(__file__).resolve().parents[1] / "packaging" / "launcher" / "main.py"
    spec = importlib.util.spec_from_file_location("launcher_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_find_existing_instance_port_waits_for_recorded_port(tmp_path, monkeypatch):
    launcher = _load_launcher_module()
    monkeypatch.setattr(launcher, "_logs_dir", lambda: tmp_path)
    launcher._write_active_port(8503)

    waited_on_ports: list[int] = []
    monkeypatch.setattr(
        launcher,
        "_wait_for_streamlit_ready",
        lambda port, timeout: waited_on_ports.append(port) or True,
    )

    assert launcher._find_existing_instance_port(launcher.STARTUP_TIMEOUT_SECONDS) == 8503
    assert waited_on_ports == [8503]


def test_find_existing_instance_port_clears_stale_state(tmp_path, monkeypatch):
    launcher = _load_launcher_module()
    monkeypatch.setattr(launcher, "_logs_dir", lambda: tmp_path)
    launcher._write_active_port(8504)

    monkeypatch.setattr(launcher, "_wait_for_streamlit_ready", lambda port, timeout: False)
    monkeypatch.setattr(launcher, "_is_port_available", lambda port: True)
    monkeypatch.setattr(launcher, "_is_streamlit_ready", lambda port: False)

    assert launcher._find_existing_instance_port(launcher.STARTUP_TIMEOUT_SECONDS) is None
    assert launcher._read_active_port() is None


def test_main_reuses_existing_instance_without_starting_new_server(monkeypatch):
    launcher = _load_launcher_module()
    logger = logging.getLogger("test.launcher")

    monkeypatch.setattr(launcher, "_configure_logger", lambda: logger)
    monkeypatch.setattr(launcher, "_find_existing_instance_port", lambda timeout: 8502)

    written_ports: list[int] = []
    monkeypatch.setattr(launcher, "_write_active_port", written_ports.append)

    opened_ports: list[int] = []
    monkeypatch.setattr(launcher, "_open_browser", lambda port, _logger: opened_ports.append(port))
    monkeypatch.setattr(
        launcher,
        "_run_streamlit",
        lambda app_path, port: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    assert launcher.main() == 0
    assert written_ports == [8502]
    assert opened_ports == [8502]


def test_run_streamlit_sets_runtime_overrides(monkeypatch):
    launcher = _load_launcher_module()

    config_options: dict[str, object] = {}
    bootstrap_calls: list[tuple[str, bool, list[str], dict[str, object]]] = []

    fake_streamlit = ModuleType("streamlit")
    fake_config = ModuleType("streamlit.config")
    fake_config.set_option = lambda name, value: config_options.__setitem__(name, value)
    fake_streamlit.config = fake_config

    fake_streamlit_web = ModuleType("streamlit.web")
    fake_bootstrap = ModuleType("streamlit.web.bootstrap")
    fake_bootstrap.run = (
        lambda app_path, is_hello, args, flags: bootstrap_calls.append(
            (app_path, is_hello, args, flags)
        )
    )
    fake_streamlit_web.bootstrap = fake_bootstrap

    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "streamlit.config", fake_config)
    monkeypatch.setitem(sys.modules, "streamlit.web", fake_streamlit_web)
    monkeypatch.setitem(sys.modules, "streamlit.web.bootstrap", fake_bootstrap)

    launcher._run_streamlit("app.py", 8506)

    assert bootstrap_calls == [("app.py", False, [], {})]
    assert config_options["server.address"] == launcher.LOCALHOST
    assert config_options["server.baseUrlPath"] == ""
    assert config_options["server.runOnSave"] is False
    assert config_options["server.fileWatcherType"] == "none"
    assert launcher.os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] == "none"
    assert launcher.os.environ["STREAMLIT_SERVER_BASE_URL_PATH"] == ""
