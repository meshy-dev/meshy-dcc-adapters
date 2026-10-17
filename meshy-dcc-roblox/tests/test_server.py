import subprocess
import sys
from types import SimpleNamespace

from meshy_dcc_roblox import _safe_stop, server
from meshy_dcc_roblox.dispatcher import dispatch


def test_server_starts_not_ready_without_a_studio_session():
    instance = server.RobloxDccServer(port=0)
    try:
        assert instance._execution_bridge.resolve_host_dispatcher() is instance._host_dispatcher
        report = instance._readiness_binder.report_subset()
        assert report["process"] is True and report["skill_catalog"] is True
        assert report["dcc"] is False and report["host_execution_bridge"] is False
    finally:
        instance.stop()


def fake_server(studio=None):
    return SimpleNamespace(instance_id="abc", studio=studio, stop_requested=server.threading.Event())


def test_stop_needs_the_instance_and_consent_to_discard():
    studio = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        stub = fake_server(studio)
        assert _safe_stop.handle_stop_request({"instance_id": "other"}, stub)[1]["reason"] == "instance_mismatch"
        status, reply = _safe_stop.handle_stop_request({"instance_id": "abc"}, stub)
        assert (status, reply["reason"]) == (409, "unsaved_changes")
        assert studio.poll() is None
        status, reply = _safe_stop.handle_stop_request({"instance_id": "abc", "discard_unsaved": True}, stub)
        assert (status, reply) == (202, {"stopping": True})
        assert studio.wait(timeout=10) is not None and stub.stop_requested.is_set()
    finally:
        studio.kill()


def test_stop_refuses_when_no_launched_studio_is_running():
    status, reply = _safe_stop.handle_stop_request({"instance_id": "abc", "discard_unsaved": True}, fake_server())
    assert (status, reply["reason"]) == (409, "host_refused")


def test_dispatch_routes_the_tool_name_and_marks_dirty_unknown(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "meshy_dcc_roblox.dispatcher.call_host",
        lambda method, params: calls.append((method, params)) or {"place": {"name": "Castle"}},
    )
    result = dispatch("roblox_scene__session", {})
    assert calls == [("session", {})]
    assert result["context"]["dirty"] is None and result["context"]["place"] == {"name": "Castle"}
