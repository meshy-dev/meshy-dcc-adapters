from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import meshy_dcc_core

import meshy_dcc_unreal

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_first_editor_tick_runs_inside_core_bootstrap_capture(monkeypatch) -> None:
    captured = []
    callbacks = []

    @contextmanager
    def capture(dcc_name, **metadata):
        captured.append((dcc_name, metadata))
        yield

    class ToolMenus:
        @staticmethod
        def get():
            return None

    fake_unreal = SimpleNamespace(
        SystemLibrary=SimpleNamespace(get_engine_version=lambda: "5.7.0"),
        ToolMenus=ToolMenus,
        is_editor=lambda: True,
        register_slate_post_tick_callback=lambda callback: callbacks.append(callback) or "tick-handle",
        unregister_slate_post_tick_callback=lambda _handle: None,
        log=lambda _message: None,
        log_warning=lambda _message: None,
    )
    handle = SimpleNamespace(mcp_url=lambda: "http://127.0.0.1:1234/mcp")
    monkeypatch.setattr(meshy_dcc_core, "capture_bootstrap_errors", capture)
    monkeypatch.setattr(meshy_dcc_unreal, "start_server", lambda **_kwargs: handle)
    monkeypatch.setitem(sys.modules, "unreal", fake_unreal)

    path = REPO_ROOT / "unreal" / "plugin" / "Content" / "Python" / "init_unreal.py"
    spec = importlib.util.spec_from_file_location("meshy_dcc_unreal_test_init", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(callbacks) == 1

    callbacks[0](0.0)

    assert captured == [
        (
            "unreal",
            {
                "adapter_version": meshy_dcc_unreal.__version__,
                "min_core_version": "0.2.0",
                "phase": "bootstrap",
                "log_dir": str(path.parents[3] / ".meshy-dcc" / "bootstrap-errors"),
                "metadata": {"runtime_mode": "python"},
            },
        )
    ]


def test_manual_startup_helper_uses_the_same_bootstrap_capture(monkeypatch) -> None:
    captured = []

    @contextmanager
    def capture(dcc_name, **metadata):
        captured.append((dcc_name, metadata))
        yield

    fake_unreal = SimpleNamespace(log=lambda _message: None)
    handle = SimpleNamespace(mcp_url=lambda: "http://127.0.0.1:1234/mcp")
    monkeypatch.setattr(meshy_dcc_core, "capture_bootstrap_errors", capture)
    monkeypatch.setattr(meshy_dcc_unreal, "start_server", lambda **_kwargs: handle)
    monkeypatch.setitem(sys.modules, "unreal", fake_unreal)

    path = REPO_ROOT / "unreal" / "plugin" / "Content" / "Python" / "meshy_dcc_unreal_startup.py"
    spec = importlib.util.spec_from_file_location("meshy_dcc_unreal_test_manual_startup", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert captured == [
        (
            "unreal",
            {
                "adapter_version": meshy_dcc_unreal.__version__,
                "min_core_version": "0.2.0",
                "phase": "bootstrap",
                "log_dir": str(path.parents[3] / ".meshy-dcc" / "bootstrap-errors"),
                "metadata": {"runtime_mode": "manual-python"},
            },
        )
    ]
