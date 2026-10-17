"""The uiready.py autostart starts one GUI server and stays out of background jobs."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import meshy_dcc_houdini
from meshy_dcc_houdini._autostart import autostart

HOOK = Path(__file__).resolve().parents[1] / "packaging" / "houdini" / "uiready.py"


@pytest.fixture
def started(monkeypatch):
    calls = []
    monkeypatch.setattr(meshy_dcc_houdini, "start_server", lambda **kwargs: calls.append(kwargs) or "server")
    monkeypatch.setitem(sys.modules, "hou", SimpleNamespace(isUIAvailable=lambda: True))
    return calls


@pytest.mark.parametrize(
    "environ",
    [
        {"MESHY_DCC_HOUDINI_AUTOSTART": "0"},
        {"MESHY_DCC_HOUDINI_AUTOSTART": "off"},
        {"MESHY_DCC_BACKGROUND_RENDER": "1"},
        {"MESHY_DCC_BACKGROUND_COOK": "1"},
    ],
)
def test_disabled_or_background_sessions_start_nothing(started, environ):
    assert autostart(environ) is None
    assert started == []


def test_headless_sessions_start_nothing(started, monkeypatch):
    monkeypatch.setitem(sys.modules, "hou", SimpleNamespace(isUIAvailable=lambda: False))
    assert autostart({}) is None
    assert started == []


def test_gui_session_starts_with_the_callers_gateway_and_registry(started):
    assert autostart({"MESHY_DCC_GATEWAY_PORT": "29765", "MESHY_DCC_REGISTRY_DIR": "/r"}) == "server"
    assert started == [{"gateway_port": 29765, "registry_dir": "/r", "wait_ready": False}]


def test_hook_puts_the_package_lib_on_sys_path_and_never_raises(tmp_path, monkeypatch, capsys):
    lib = tmp_path / "lib"
    lib.mkdir()
    monkeypatch.setenv("MESHY_DCC_HOUDINI_ROOT", str(tmp_path))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr("meshy_dcc_houdini._autostart.autostart", lambda: 1 / 0)
    exec(compile(HOOK.read_text(encoding="utf-8"), str(HOOK), "exec"), {})
    assert sys.path[0] == str(lib)
    assert "Meshy DCC autostart failed" in capsys.readouterr().out
