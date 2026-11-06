"""Client lost-reply regression tests for the ZBrush socket bridge.

Once a real method is on the wire the host may already be running it, so a
lost, empty or malformed reply, or a connection reset, abort, broken pipe, EOF
or timeout after the connection was made, is ``-32002 execution_state=unknown,
retryable=False`` and is never replayed. A failure before the connection exists
stays bare, so the "unreachable" diagnosis survives. These tests use transport
doubles and loopback peers; they are not native ZBrush evidence.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
from unittest.mock import MagicMock

import pytest

from meshy_dcc_zbrush import api
from meshy_dcc_zbrush import bridge as bridge_mod
from meshy_dcc_zbrush.bridge import STATUS_BLOCKED, SocketBridge, ZBrushBlockedError, ZBrushBridgeError


def _assert_unknown_outcome(error: ZBrushBridgeError) -> None:
    assert error.code == -32002
    assert error.data["execution_state"] == "unknown"
    assert error.data["retryable"] is False
    assert error.data["active_method"] == "execute_python"


@pytest.mark.parametrize("invalid", [b"", b"{", b"\xff", b"[]", b"{}"])
def test_invalid_reply_after_submit_is_unknown_and_not_replayed(monkeypatch, invalid):
    bridge = SocketBridge()
    sent = []

    def send(data, **_kwargs):
        sent.append(json.loads(data)["method"])
        return invalid

    monkeypatch.setattr(bridge, "_send", send)
    with pytest.raises(ZBrushBridgeError) as caught:
        bridge.call("execute_python")

    _assert_unknown_outcome(caught.value)
    assert sent == ["execute_python"]


class _StageSocket:
    """``create_connection`` result whose sendall/recv fail, so the real ``_send`` marks them."""

    def __init__(self, sent, recv_exc=None, sendall_exc=None):
        self._sent = sent
        self._recv_exc = recv_exc
        self._sendall_exc = sendall_exc

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def sendall(self, data):
        self._sent.append(json.loads(data)["method"])
        if self._sendall_exc is not None:
            raise self._sendall_exc

    def recv(self, _n):
        if self._recv_exc is not None:
            raise self._recv_exc
        return b""  # clean EOF


def _stage_socket(monkeypatch, **kwargs):
    sent = []
    sock = _StageSocket(sent, **kwargs)
    monkeypatch.setattr(bridge_mod.socket, "create_connection", lambda *a, **k: sock)
    return sent


@pytest.mark.parametrize(
    "exc",
    [
        ConnectionResetError("reset"),
        ConnectionAbortedError("abort"),
        BrokenPipeError("pipe"),
        TimeoutError("no reply"),
        OSError("lost"),
    ],
)
@pytest.mark.parametrize("stage", ["recv_exc", "sendall_exc"])
def test_connection_loss_after_connect_is_unknown_and_not_replayed(monkeypatch, exc, stage):
    bridge = SocketBridge(host="127.0.0.1", port=19876)
    bridge._connected = True
    sent = _stage_socket(monkeypatch, **{stage: exc})

    with pytest.raises(ZBrushBridgeError) as caught:
        bridge.call("execute_python", code="x = 1")

    _assert_unknown_outcome(caught.value)
    assert sent == ["execute_python"]  # one submission, no retry
    assert bridge.is_connected() is False


def test_failure_before_connect_stays_bare(monkeypatch):
    bridge = SocketBridge(host="127.0.0.1", port=19876)
    bridge._connected = True

    def refuse(*_a, **_k):
        raise ConnectionRefusedError("nothing listening")

    monkeypatch.setattr(bridge_mod.socket, "create_connection", refuse)

    with pytest.raises(ConnectionRefusedError, match="nothing listening"):
        bridge.call("get_session_info")
    assert bridge.is_connected() is False


def test_real_tcp_eof_after_submit_is_unknown():
    received = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(2)

        def peer():
            # The host reads the submitted work and closes without replying.
            with listener.accept()[0] as conn:
                received.append(json.loads(conn.recv(65536))["method"])

        thread = threading.Thread(target=peer)
        thread.start()
        try:
            with pytest.raises(ZBrushBridgeError) as caught:
                SocketBridge(port=listener.getsockname()[1], timeout=1).call("execute_python")
        finally:
            thread.join(2)

    _assert_unknown_outcome(caught.value)
    assert received == ["execute_python"]


def test_real_tcp_reset_after_submit_is_unknown():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(3)

        def peer():
            conn, _ = listener.accept()
            with conn:
                conn.settimeout(3)
                conn.recv(65536)
                # Force a real TCP RST once the host has read the work.
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))

        thread = threading.Thread(target=peer)
        thread.start()
        try:
            with pytest.raises(ZBrushBridgeError) as caught:
                SocketBridge(port=listener.getsockname()[1], timeout=2).call("execute_python")
        finally:
            thread.join(3)

    _assert_unknown_outcome(caught.value)


def test_unknown_outcome_at_tool_boundary_says_inspect_before_retrying(monkeypatch):
    bridge = SocketBridge(host="127.0.0.1", port=19876)
    bridge._connected = True
    _stage_socket(monkeypatch, recv_exc=ConnectionResetError("reset after submit"))
    monkeypatch.setattr(api, "_bridge", bridge)

    @api.with_zbrush
    def call_lost(**_kwargs):
        return api.get_bridge().call("execute_python", code="x=1")

    result = call_lost()

    assert result["error"] == "ZBRUSH_TIMEOUT_STILL_RUNNING"
    assert result["context"]["execution_state"] == "unknown"
    assert result["context"]["retryable"] is False
    assert "Inspect ZBrush before retrying" in result["prompt"]


def test_probe_reset_after_accept_is_blocked_not_unreachable(monkeypatch):
    bridge = SocketBridge(host="127.0.0.1", port=19876)
    _stage_socket(monkeypatch, recv_exc=ConnectionResetError("reset after accept"))

    verdict = bridge.probe()

    assert verdict["status"] == STATUS_BLOCKED
    assert "listening" not in verdict["message"].lower()


def test_get_bridge_keeps_the_blocked_verdict_on_reconnect(monkeypatch):
    bridge = SocketBridge(host="127.0.0.1", port=19876)
    verdict = {"status": "blocked", "message": "main thread is in a native call", "endpoint": bridge.endpoint}
    monkeypatch.setattr(bridge, "connect", MagicMock(side_effect=ZBrushBlockedError("stuck", detail=verdict)))
    monkeypatch.setattr(api, "_bridge", bridge)

    @api.with_zbrush
    def reconnect_then_call(**_kwargs):
        return api.get_bridge().call("execute_python", code="x=1")

    result = reconnect_then_call()

    assert result["error"] == "ZBRUSH_BLOCKED"
    assert "Do not retry automatically" in result["prompt"]
    assert result["context"]["blocked"]["status"] == "blocked"
