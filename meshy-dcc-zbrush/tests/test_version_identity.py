"""``zbrush_info(1)`` is the edition (0 Demo, 1 Beta, 2 Full), never a minor version."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

import meshy_dcc_zbrush._version_probe as probe
import meshy_dcc_zbrush.install_lifecycle as lifecycle
from tests.test_socket_bridge_plugin import _load_bridge_plugin

_ROOT = Path(__file__).parent.parent


class _FakeZbc:
    def __init__(self, version: float, edition: float) -> None:
        self._info = {0: version, 1: edition}
        self.__file__ = ""

    def zbrush_info(self, index: int) -> float:
        return self._info[index]

    def get_active_tool_path(self) -> str:
        return ""

    def get_subtool_count(self) -> int:
        return 0


@pytest.mark.parametrize(
    "version, expected",
    [(2027.0, "2027.0"), (2026.1, "2026.1"), (2027, "2027.0"), (2028.25, "2028.25"), (2027.001, "2027.001")],
)
def test_sdk_version_keeps_its_precision_with_two_components(version, expected):
    assert probe.format_sdk_version(version) == expected


@pytest.mark.parametrize("edition", [0, 1, 2])
def test_version_does_not_depend_on_the_edition(edition):
    assert probe.read_sdk_version(_FakeZbc(2027.0, edition)) == ("2027.0", edition)


def test_unreadable_edition_is_minus_one():
    zbc = MagicMock()
    zbc.zbrush_info.side_effect = [2027.0, TypeError("no edition")]
    assert probe.read_sdk_version(zbc) == ("2027.0", -1)


def test_probe_reports_version_and_edition_separately(monkeypatch):
    zbrush = ModuleType("zbrush")
    commands = _FakeZbc(2027.0, 2)
    monkeypatch.setitem(sys.modules, "zbrush", zbrush)
    monkeypatch.setitem(sys.modules, "zbrush.commands", commands)

    assert probe.get_zbrush_version_string() == "2027.0"
    assert probe.get_zbrush_edition() == 2
    assert probe.get_zbrush_version_tuple() == (2027, 0)


def test_plugin_session_info_keeps_edition_out_of_version(tmp_path, monkeypatch):
    bridge = _load_bridge_plugin()
    bridge_file = tmp_path / "meshy_dcc_zbrush_socket_bridge.py"
    bridge_file.write_text("# placeholder\n", encoding="utf-8")
    identity = {"adapter_version": "0.1.3", "zbrush_version": "2027.0.1", "dcc_sha256": "ab"}
    (tmp_path / "meshy_dcc_zbrush_install_identity.json").write_text(json.dumps(identity), encoding="utf-8")
    monkeypatch.setattr(bridge, "_BRIDGE_FILE", str(bridge_file))
    monkeypatch.setattr(bridge, "_import_zbc", lambda: _FakeZbc(2027.0, 2))

    info = bridge._get_session_info()

    assert info["zbrush_version"] == "2027.0"
    assert info["zbrush_edition"] == 2
    assert info["zbrush_product_version"] == "2027.0.1"
    assert "2027.2" not in json.dumps(info)


def test_plugin_server_info_labels_the_edition(monkeypatch):
    bridge = _load_bridge_plugin()
    monkeypatch.setitem(sys.modules, "zbrush", ModuleType("zbrush"))
    monkeypatch.setitem(sys.modules, "zbrush.commands", _FakeZbc(2027.0, 2))
    shown = {}
    monkeypatch.setattr(bridge, "_show_message", lambda _title, msg: shown.update(msg=msg))

    bridge._fallback_server_info()

    assert "ZBrush 2027.0 (Full edition)" in shown["msg"]


def test_embedded_session_info_keeps_edition_out_of_version(tmp_path, monkeypatch):
    path = _ROOT / "src/meshy_dcc_zbrush/skills/zbrush-scripting/scripts/get_session_info.py"
    spec = importlib.util.spec_from_file_location("version_identity_get_session_info", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps({"zbrush_version": "2027.0.1", "dcc_sha256": "ab"}), encoding="utf-8")
    monkeypatch.setenv("MESHY_DCC_ZBRUSH_INSTALL_IDENTITY", str(identity))

    info = module._collect(_FakeZbc(2027.0, 2))

    assert (info["zbrush_version"], info["zbrush_edition"]) == ("2027.0", 2)
    assert info["zbrush_product_version"] == "2027.0.1"


@pytest.mark.parametrize(
    "host, sdk, product",
    [
        ("2026.1.0.0", "2026.0", "2026.1.0.0"),
        ("2027.0.1", "2027.001", "2027.0.1"),  # a float fraction with leading zeros
        ("2026, 2, 1, 1", "2026.0", "2026, 2, 1, 1"),
        ("2026.1.0.0", "2026.0", ""),  # a host that does not report its ProductVersion
    ],
)
def test_matching_host_is_consistent_whatever_the_edition(host, sdk, product):
    session = {"zbrush_version": sdk, "zbrush_product_version": product}
    assert lifecycle._host_version_is_consistent(session, {"host_version": host}) is True


@pytest.mark.parametrize(
    "sdk, product",
    [("2026.0", "2027.0.1"), ("2027.0", "2099.0.0"), ("", "2027.0.1"), ("2027.0" + "0" * 80, ""), ("x", "")],
)
def test_other_host_is_rejected(sdk, product):
    session = {"zbrush_version": sdk, "zbrush_product_version": product}
    assert lifecycle._host_version_is_consistent(session, {"host_version": "2027.0.1"}) is False
