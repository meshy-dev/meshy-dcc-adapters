import json
import socket
import threading
import time
import urllib.request

import pytest
from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import connect

from meshy_dcc_roblox import bridge as bridge_module
from meshy_dcc_roblox.bridge import RobloxBridge, place_matches


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def running():
    started = []

    def start(expect=None):
        changes = []
        bridge = RobloxBridge(port=free_port(), expect=expect, on_change=lambda: changes.append(bridge.is_connected()), timeout=5)
        bridge.connect()
        started.append(bridge)
        return bridge, changes

    yield start
    for bridge in started:
        bridge.disconnect()


def hello(ws, name="Castle.rbxl", place_id=0):
    ws.send(json.dumps({"type": "hello", "client": "roblox-studio", "version": "0.700", "place": {"name": name, "place_id": place_id}}))
    return json.loads(ws.recv(timeout=5))


def probe(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
        return json.loads(response.read())


def test_place_matching():
    assert place_matches({}, {"name": "anything"})
    assert place_matches({"place_file": "Castle.rbxl"}, {"name": "Castle", "place_id": 0})
    assert place_matches({"place_file": "Castle.rbxl"}, {"name": "castle.rbxl", "place_id": 0})
    assert not place_matches({"place_file": "Castle.rbxl"}, {"name": "Castle", "place_id": 42})
    assert not place_matches({"place_file": "Castle.rbxl"}, {"name": "Baseplate", "place_id": 0})
    assert place_matches({"place_id": 42}, {"name": "x", "place_id": 42})
    assert not place_matches({"place_id": 42}, {"name": "x", "place_id": 43})


def test_plugin_of_the_expected_place_binds_and_answers_calls(running):
    bridge, changes = running({"place_file": "Castle.rbxl"})
    port = bridge._port
    assert probe(port)["accepting"] is True
    with connect(f"ws://127.0.0.1:{port}/") as ws:
        assert hello(ws)["type"] == "hello_ack"
        assert bridge.place["name"] == "Castle.rbxl" and bridge.studio_version == "0.700"
        assert probe(port)["accepting"] is False

        def plugin():
            request = json.loads(ws.recv(timeout=5))
            assert request["method"] == "get_scene_tree" and request["params"] == {"root": "Workspace"}
            ws.send(json.dumps({"type": "response", "id": request["id"], "result": {"nodes": []}}))

        thread = threading.Thread(target=plugin)
        thread.start()
        assert bridge.call("get_scene_tree", root="Workspace") == {"nodes": []}
        thread.join()
    deadline = time.monotonic() + 5
    while bridge.place is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    assert changes[0] is True and changes[-1] is False
    assert bridge.place is None


def test_other_places_and_second_sessions_are_refused(running):
    bridge, _ = running({"place_file": "Castle.rbxl"})
    url = f"ws://127.0.0.1:{bridge._port}/"
    with connect(url) as other:
        reply = hello(other, name="Baseplate")
        assert reply == {"type": "hello_reject", "reason": "place_mismatch", "expect": {"place_file": "Castle.rbxl"}}
        with pytest.raises(ConnectionClosed):
            other.recv(timeout=5)
    with connect(url) as first, connect(url) as second:
        assert hello(first)["type"] == "hello_ack"
        assert hello(second)["reason"] == "busy"
        assert bridge.place["name"] == "Castle.rbxl"


def test_browser_origins_are_refused(running):
    bridge, _ = running()
    with pytest.raises(InvalidStatus) as refused:
        connect(f"ws://127.0.0.1:{bridge._port}/", origin="https://example.com")
    assert refused.value.response.status_code == 403


def test_plugin_errors_become_rpc_errors(running):
    from meshy_dcc_core.bridge import BridgeRpcError

    bridge, _ = running()
    with connect(f"ws://127.0.0.1:{bridge._port}/") as ws:
        hello(ws)

        def plugin():
            request = json.loads(ws.recv(timeout=5))
            ws.send(json.dumps({"type": "response", "id": request["id"], "error": {"code": -32000, "message": "no instance at Workspace/X"}}))

        thread = threading.Thread(target=plugin)
        thread.start()
        with pytest.raises(BridgeRpcError, match="no instance"):
            bridge.call("inspect_instance", path="Workspace/X")
        thread.join()


def test_pick_port_skips_taken_ports(monkeypatch):
    monkeypatch.delenv("MESHY_DCC_ROBLOX_BRIDGE_PORT", raising=False)
    ports = (free_port(), free_port())
    monkeypatch.setattr(bridge_module, "PORTS", ports)
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", ports[0]))
        taken.listen()
        assert bridge_module.pick_port() == ports[1]


def test_plugin_ports_match_the_sidecar():
    from pathlib import Path

    source = (Path(bridge_module.__file__).parent / "plugin" / "MeshyDcc.lua").read_text(encoding="utf-8")
    ports = ", ".join(str(port) for port in bridge_module.PORTS)
    assert f"local PORTS = {{ {ports} }}" in source
