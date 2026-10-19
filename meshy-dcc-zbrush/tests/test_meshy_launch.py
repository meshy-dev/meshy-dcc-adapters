"""Meshy DCC launch path: project setup, bridge token and sidecar start, save/open, safe stop."""

from __future__ import annotations

import importlib.util
import json
import socket
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _load_bridge_plugin() -> ModuleType:
    path = Path(__file__).parent.parent / "bridge" / "plugin" / "mcp_socket_bridge.py"
    spec = importlib.util.spec_from_file_location("mcp_socket_bridge_launch", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── setup-project ───────────────────────────────────────────────────────────


def test_setup_project_writes_a_script_launch_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import meshy_dcc_zbrush.install_lifecycle as lifecycle
    import meshy_dcc_zbrush.project_setup as setup

    bridge = tmp_path / "pkg" / "mcp_socket_bridge.py"
    bridge.parent.mkdir()
    bridge.write_text("# bridge\n", encoding="utf-8")
    zbrush = tmp_path / "ZBrush"
    monkeypatch.setattr(setup, "bridge_script", lambda: bridge)
    monkeypatch.setattr(
        lifecycle,
        "_probe_zbrush_host",
        lambda path: {"dcc_path": str(zbrush), "zbrush_version": "2026.2.0"},
    )
    project = tmp_path / "work"
    project.mkdir()

    code = setup.main([str(project), "--dcc-path", str(zbrush), "--json"])

    report = json.loads(capsys.readouterr().out)
    plan = json.loads((project / ".meshy-dcc" / "launch-plan.json").read_text(encoding="utf-8"))
    assert code == 0 and report["status"] == "installed"
    assert plan == {
        "schema_version": 1,
        "dcc_type": "zbrush",
        "executable": str(zbrush),
        "argv": ["{executable}", "-script", str(bridge)],
        "version": "2026.2.0",
    }
    assert (project / ".meshy-dcc" / ".gitignore").read_text(encoding="utf-8") == "*\n"


def test_setup_project_reports_failure_as_json(tmp_path: Path, capsys) -> None:
    from meshy_dcc_zbrush.cli import main

    code = main(["setup-project", "relative/folder", "--dcc-path", str(tmp_path / "ZBrush"), "--json"])

    report = json.loads(capsys.readouterr().out)
    assert code == 10
    assert report["status"] == "failed" and "absolute" in report["reason"]


# ── bridge token and sidecar start ─────────────────────────────────────────


def test_bridge_requires_its_token_when_it_has_one() -> None:
    bridge = _load_bridge_plugin()
    assert bridge._token_accepted({"method": "ping"})

    bridge._BRIDGE_TOKEN = "secret"
    assert not bridge._token_accepted({"method": "ping"})
    assert not bridge._token_accepted({"method": "ping", "token": "wrong"})
    assert not bridge._token_accepted({"method": "ping", "token": 7})
    assert bridge._token_accepted({"method": "ping", "token": "secret"})


def test_bridge_refuses_a_request_without_the_token() -> None:
    bridge = _load_bridge_plugin()
    bridge._BRIDGE_TOKEN = "secret"
    bridge._route_request = MagicMock()
    ours, theirs = socket.socketpair()
    with theirs:
        theirs.sendall(b'{"jsonrpc": "2.0", "id": 3, "method": "execute_python"}\n')
        bridge._serve_client(ours)
        reply = json.loads(theirs.recv(65536).decode("utf-8"))

    assert reply["error"]["code"] == -32003
    bridge._route_request.assert_not_called()


def test_bridge_finds_the_package_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _load_bridge_plugin()
    plugin = tmp_path / "python" / "lib" / "python3.11" / "site-packages" / "meshy_dcc_zbrush" / "plugin"
    plugin.mkdir(parents=True)
    interpreter = tmp_path / "python" / "bin" / "python3"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("", encoding="utf-8")
    monkeypatch.setattr(bridge, "_BRIDGE_FILE", str(plugin / "mcp_socket_bridge.py"))

    assert bridge._package_python() == str(interpreter)


def test_bridge_starts_its_sidecar_on_the_bound_port_before_the_pump(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _load_bridge_plugin()
    order: list[str] = []
    popen = MagicMock(side_effect=lambda *args, **kwargs: order.append("sidecar"))
    monkeypatch.setattr(bridge.subprocess, "Popen", popen)
    monkeypatch.setattr(bridge, "_install_main_thread_pump", lambda: order.append("pump"))
    monkeypatch.setenv("PYTHONHOME", "/zbrush/python")
    bridge._BRIDGE_TOKEN = "secret"

    bridge._start_bridge("127.0.0.1", 0, "/pkg/python/bin/python3")

    argv = popen.call_args.args[0]
    env = popen.call_args.kwargs["env"]
    port = int(argv[argv.index("--socket-port") + 1])
    assert order == ["sidecar", "pump"]
    assert argv[:4] == ["/pkg/python/bin/python3", "-m", "meshy_dcc_zbrush", "serve"]
    assert port > 0
    assert env["MESHY_DCC_ZBRUSH_BRIDGE_TOKEN"] == "secret"
    assert "PYTHONHOME" not in env
    with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
        client.sendall(b'{"jsonrpc": "2.0", "id": 1, "method": "ping", "token": "secret"}\n')
        assert json.loads(client.recv(65536).decode("utf-8"))["result"]["ok"] is True


def test_socket_bridge_sends_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from meshy_dcc_zbrush.bridge import SocketBridge

    monkeypatch.setenv("MESHY_DCC_ZBRUSH_BRIDGE_TOKEN", "secret")
    assert SocketBridge()._payload("ping", {})["token"] == "secret"
    monkeypatch.delenv("MESHY_DCC_ZBRUSH_BRIDGE_TOKEN")
    assert "token" not in SocketBridge()._payload("ping", {})


# ── save and open ───────────────────────────────────────────────────────────


def _saving_zbc(content: bytes = b"zpr") -> MagicMock:
    zbc = MagicMock()
    zbc.exists.return_value = True
    zbc.get_active_tool_path.return_value = "Tools/Dragon"
    zbc.get_subtool_count.return_value = 2
    target: dict[str, str] = {}
    zbc.set_next_filename.side_effect = lambda path: target.update(path=path)
    zbc.press.side_effect = lambda _control: Path(target["path"]).write_bytes(content)
    return zbc


def test_bridge_saves_a_project_to_the_exact_path(tmp_path: Path) -> None:
    bridge = _load_bridge_plugin()
    zbc = _saving_zbc()
    bridge._import_zbc = lambda: zbc

    result = bridge._save_file("project", str(tmp_path / "work.zpr"), False)

    assert result["path"] == str(tmp_path / "work.zpr") and result["bytes"] == 3
    zbc.press.assert_called_once_with("File:Save As")
    assert zbc.show_actions.call_args_list[-1].args == (1,)


def test_bridge_refuses_to_replace_a_file_unless_asked(tmp_path: Path) -> None:
    bridge = _load_bridge_plugin()
    zbc = _saving_zbc()
    bridge._import_zbc = lambda: zbc
    existing = tmp_path / "dragon.ztl"
    existing.write_bytes(b"old")

    refused = bridge._save_file("tool", str(existing), False)
    replaced = bridge._save_file("tool", str(existing), True)

    assert refused["error"] == "FILE_EXISTS"
    assert replaced["bytes"] == 3 and existing.read_bytes() == b"zpr"
    zbc.press.assert_called_once_with("Tool:Save As")
    assert list(tmp_path.iterdir()) == [existing]


def test_bridge_puts_the_old_file_back_when_a_save_writes_nothing(tmp_path: Path) -> None:
    bridge = _load_bridge_plugin()
    zbc = _saving_zbc(content=b"")
    bridge._import_zbc = lambda: zbc
    existing = tmp_path / "work.zpr"
    existing.write_bytes(b"old")

    with pytest.raises(RuntimeError, match="non-empty .zpr"):
        bridge._save_file("project", str(existing), True)

    assert existing.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [existing]


def test_bridge_rejects_a_save_with_the_wrong_extension(tmp_path: Path) -> None:
    bridge = _load_bridge_plugin()
    bridge._import_zbc = MagicMock(side_effect=AssertionError("must not reach ZBrush"))

    assert bridge._save_file("project", str(tmp_path / "work.ztl"), False)["error"] == "UNSUPPORTED_FORMAT"
    assert bridge._save_file("scene", str(tmp_path / "work.zpr"), False)["error"] == "UNSUPPORTED_KIND"


def test_bridge_opens_a_project_and_reads_it_back(tmp_path: Path) -> None:
    bridge = _load_bridge_plugin()
    zbc = _saving_zbc()
    bridge._import_zbc = lambda: zbc
    project = tmp_path / "work.zpr"
    project.write_bytes(b"zpr")

    result = bridge._open_project(str(project))

    zbc.set_next_filename.assert_called_once_with(str(project))
    zbc.press.assert_called_once_with("File:Open")
    assert result == {"path": str(project), "active_tool_path": "Tools/Dragon", "subtool_count": 2}
    assert bridge._open_project(str(tmp_path / "missing.zpr"))["error"] == "FILE_NOT_FOUND"


# ── safe stop ───────────────────────────────────────────────────────────────


def test_safe_stop_refuses_without_discard_and_ends_zbrush_with_it() -> None:
    from meshy_dcc_zbrush._safe_stop import handle_stop_request

    terminate = MagicMock()

    assert handle_stop_request({"instance_id": "other"}, "abc", 42, terminate)[1]["reason"] == "instance_mismatch"
    status, reply = handle_stop_request({"instance_id": "abc"}, "abc", 42, terminate)
    assert (status, reply["reason"]) == (409, "unsaved_changes")
    terminate.assert_not_called()

    assert handle_stop_request({"instance_id": "abc", "discard_unsaved": True}, "abc", 42, terminate) == (
        202,
        {"stopping": True},
    )
    terminate.assert_called_once_with(42)


def test_safe_stop_is_only_offered_for_a_start_instance_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    from meshy_dcc_zbrush._safe_stop import attach_safe_stop

    server = MagicMock(dcc_pid=4242)
    monkeypatch.delenv("MESHY_DCC_START_OPERATION_ID", raising=False)
    attach_safe_stop(server)
    server._handle.update_gateway_metadata.assert_not_called()

    monkeypatch.setenv("MESHY_DCC_START_OPERATION_ID", "op-1")
    attach_safe_stop(server)
    url = server._handle.update_gateway_metadata.call_args.args[0]["safe_stop_url"]
    assert url.startswith("http://127.0.0.1:") and url.endswith("/safe-stop")


def test_sidecar_runs_main_thread_tools_inline() -> None:
    """Every tool declares affinity main; the bridge, not the sidecar, owns the ZBrush main thread."""
    from meshy_dcc_core._server.options import StandaloneMainThreadExecution

    from meshy_dcc_zbrush.server import ZBrushServerOptions

    sidecar = ZBrushServerOptions(mode="sidecar").to_core_options()
    embedded = ZBrushServerOptions(mode="embedded").to_core_options()

    assert sidecar.execution.mode == StandaloneMainThreadExecution
    assert embedded.execution.mode != StandaloneMainThreadExecution
    assert sidecar.instance_type == "gui"


def test_bridge_hands_the_zbrush_version_to_its_sidecar(monkeypatch: pytest.MonkeyPatch) -> None:
    # The sidecar cannot import zbrush.commands, so `list` showed zbrush@unknown.
    bridge = _load_bridge_plugin()
    zbc = MagicMock()
    zbc.zbrush_info.side_effect = [2026, 2]
    monkeypatch.setattr(bridge, "_import_zbc", lambda: zbc)
    popen = MagicMock()
    monkeypatch.setattr(bridge.subprocess, "Popen", popen)

    bridge._start_sidecar("/pkg/python/bin/python3", 1234, "secret")

    assert popen.call_args.kwargs["env"]["MESHY_DCC_ZBRUSH_VERSION"] == "2026.2"
    from meshy_dcc_zbrush._version_probe import get_zbrush_version_string

    monkeypatch.setenv("MESHY_DCC_ZBRUSH_VERSION", "2026.2")
    assert get_zbrush_version_string() == "2026.2"
