"""Queue-deadline and client lost-reply regression tests for the ZBrush socket bridge.

The in-ZBrush main-thread pump refuses a request whose wire deadline
(``deadline_unix_ms``) or local queue timeout passed before it started, and
answers ``-32004`` with ``executed: false``. A request that already started
keeps the host busy and is reported as possibly still running.

On the client side, once a real method is on the wire the host may already be running it, so a
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
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from meshy_dcc_zbrush import api
from meshy_dcc_zbrush import bridge as bridge_mod
from meshy_dcc_zbrush.bridge import STATUS_BLOCKED, SocketBridge, ZBrushBlockedError, ZBrushBridgeError
from tests.test_socket_bridge_plugin import _load_bridge_plugin


def _wait_until_queued(plugin):
    deadline = time.monotonic() + 1
    while plugin._REQUEST_QUEUE.empty() and time.monotonic() < deadline:
        time.sleep(0.001)


def test_expired_queued_request_does_not_execute_after_pump_resumes():
    plugin = _load_bridge_plugin()
    plugin._REQUEST_TIMEOUT_SECONDS = 0.01
    handler = MagicMock(return_value={"result": {"ok": True}})
    plugin._handle_request = handler

    result = plugin._dispatch_request({"id": 1, "method": "execute_python"})
    plugin._drain_request_queue()

    handler.assert_not_called()
    assert result["error"]["code"] == -32004
    assert result["error"]["data"]["executed"] is False
    assert plugin._ACTIVE_REQUEST is None


def test_wire_deadline_rejects_request_delayed_before_plugin_accept():
    plugin = _load_bridge_plugin()
    handler = MagicMock()
    plugin._handle_request = handler

    result = plugin._dispatch_request(
        {"id": 1, "method": "execute_python", "deadline_unix_ms": (time.time() - 1) * 1000}
    )
    plugin._drain_request_queue()

    handler.assert_not_called()
    assert result["error"]["code"] == -32004
    assert plugin._REQUEST_QUEUE.empty()


def test_started_request_remains_busy_after_wait_timeout():
    plugin = _load_bridge_plugin()
    plugin._REQUEST_TIMEOUT_SECONDS = 0.3
    entered = threading.Event()
    release = threading.Event()

    def handle(payload):
        entered.set()
        assert release.wait(2)
        return {"id": payload["id"], "result": {"ok": True}}

    plugin._handle_request = handle
    with ThreadPoolExecutor(max_workers=2) as pool:
        request = pool.submit(plugin._dispatch_request, {"id": 1, "method": "execute_python"})
        _wait_until_queued(plugin)
        pump = pool.submit(plugin._drain_request_queue)
        assert entered.wait(1)
        try:
            response = request.result(timeout=1)
            assert response["error"]["code"] == -32002
            assert response["error"]["data"]["retryable"] is False
            assert plugin._dispatch_request({"id": 2})["error"]["code"] == -32001
        finally:
            release.set()
        pump.result(timeout=1)
    assert plugin._ACTIVE_REQUEST is None


def test_expiry_is_checked_on_pump_even_before_waiter_can_cancel():
    plugin = _load_bridge_plugin()
    handler = MagicMock()
    plugin._handle_request = handler
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(plugin._dispatch_request, {"id": 1, "method": "execute_python"})
        _wait_until_queued(plugin)
        with plugin._REQUEST_STATE_LOCK:
            plugin._ACTIVE_REQUEST["deadline"] = time.monotonic() - 1
        plugin._drain_request_queue()
        assert request.result(timeout=1)["error"]["code"] == -32004
    handler.assert_not_called()


def test_cancelled_queue_entries_stay_bounded():
    plugin = _load_bridge_plugin()
    plugin._REQUEST_TIMEOUT_SECONDS = 0.001
    for request_id in range(10):
        assert plugin._dispatch_request({"id": request_id})["error"]["code"] == -32004
        assert plugin._REQUEST_QUEUE.qsize() == 1
    plugin._drain_request_queue()
    assert plugin._ACTIVE_REQUEST is None


@pytest.mark.parametrize("deadline", [True, "tomorrow", float("nan"), float("inf"), 10**400])
def test_invalid_deadlines_fail_closed(deadline):
    plugin = _load_bridge_plugin()

    response = plugin._dispatch_request({"id": 1, "deadline_unix_ms": deadline})

    assert response["error"]["code"] == -32602
    assert plugin._REQUEST_QUEUE.empty()


def test_real_tcp_delayed_accept_discards_expired_host_work():
    plugin = _load_bridge_plugin()
    handler = MagicMock()
    plugin._handle_request = handler
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(2)
        with socket.create_connection(listener.getsockname(), timeout=2) as client:
            client.sendall(
                json.dumps({"id": 1, "method": "execute_python", "deadline_unix_ms": (time.time() - 1) * 1000}).encode()
                + b"\n"
            )
            # The kernel takes the data before the embedded listener resumes.
            conn, _ = listener.accept()
            plugin._serve_client(conn)
            response = json.loads(client.recv(65536))
    assert response["error"]["code"] == -32004
    plugin._drain_request_queue()
    handler.assert_not_called()


def test_aborted_started_request_releases_waiter_and_busy_slot():
    plugin = _load_bridge_plugin()
    plugin._handle_request = MagicMock(side_effect=SystemExit("abort"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(plugin._dispatch_request, {"id": 1, "method": "execute_python"})
        _wait_until_queued(plugin)
        with pytest.raises(SystemExit, match="abort"):
            plugin._drain_request_queue()
        response = request.result(timeout=1)
    assert response["error"]["code"] == -32002
    assert response["error"]["data"] == {"retryable": False, "execution_state": "unknown"}
    assert plugin._ACTIVE_REQUEST is None


def test_client_wire_deadline_is_its_own_timeout_not_the_plugin_cap(monkeypatch):
    sent = []

    def send(data, **_kwargs):
        sent.append(json.loads(data))
        return b'{"result":{"ok":true}}'

    bridge = SocketBridge(timeout=5.0)
    monkeypatch.setattr(bridge, "_send", send)
    before = time.time()
    assert bridge.call("execute_python", code="x = 1") == {"ok": True}
    after = time.time()

    wire_ms = sent[0]["deadline_unix_ms"]
    assert before * 1000 + 5000 <= wire_ms <= after * 1000 + 5000

    # The plugin turns that wire value into a ~5 s wait, well under its 600 s cap.
    plugin = _load_bridge_plugin()
    plugin._handle_request = MagicMock(return_value={"result": {"ok": True}})
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(plugin._dispatch_request, sent[0])
        _wait_until_queued(plugin)
        remaining = plugin._ACTIVE_REQUEST["deadline"] - time.monotonic()
        assert 0 < remaining < 6
        plugin._drain_request_queue()
        assert request.result(timeout=2)["result"] == {"ok": True}


def test_expired_request_error_maps_to_a_retryable_tool_error(monkeypatch):
    bridge = SocketBridge(host="127.0.0.1", port=19876)
    bridge._connected = True
    expired = {"error": {"code": -32004, "message": "expired", "data": {"retryable": True, "executed": False}}}
    monkeypatch.setattr(bridge, "_send", lambda _data, **_kw: json.dumps(expired).encode())
    monkeypatch.setattr(api, "_bridge", bridge)

    @api.with_zbrush
    def call_expired(**_kwargs):
        return api.get_bridge().call("execute_python", code="x=1")

    result = call_expired()

    assert result["error"] == "ZBRUSH_REQUEST_EXPIRED"
    assert result["context"]["executed"] is False


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
