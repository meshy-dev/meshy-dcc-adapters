"""A job whose Unity main thread stops answering ends after a threshold, not never."""

import pytest
from meshy_dcc_core.bridge import BridgeConnectionError

from meshy_dcc_unity import bridge
from meshy_dcc_unity import job_result as job_results
from meshy_dcc_unity.job_result import job_state_result

REQUEST_ID = "778e72dd-e536-4ff8-aad0-9b752ab61c3b"


@pytest.fixture
def clock(monkeypatch):
    now = {"t": 1_000.0}
    monkeypatch.setattr(bridge.time, "time", lambda: now["t"])
    monkeypatch.setattr(job_results.time, "time", lambda: now["t"])
    monkeypatch.setenv("MESHY_DCC_UNITY_UNRESPONSIVE_SECS", "120")
    yield now
    bridge.set_host_dispatch_ready(True)


def _deferred(monkeypatch, inspect):
    monkeypatch.setattr(job_results, "call_host", inspect)
    return job_state_result(
        "Unity refresh", {"request_id": REQUEST_ID, "state": "running", "phase": "refresh"}
    )


def _blocked(*_args, **_kwargs):
    raise BridgeConnectionError("the Editor main thread is not dispatching.")


def test_still_running_while_unity_answers(monkeypatch, clock):
    bridge.set_host_dispatch_ready(True)
    deferred = _deferred(monkeypatch, lambda *_a, **_k: {"state": "running", "phase": "refresh"})
    clock["t"] += 10_000
    assert deferred.check_is_finished() is None


def test_still_running_before_the_threshold(monkeypatch, clock):
    bridge.set_host_dispatch_ready(True)
    bridge.set_host_dispatch_ready(False)
    deferred = _deferred(monkeypatch, _blocked)
    clock["t"] += 119
    assert deferred.check_is_finished() is None


def test_ends_with_host_unresponsive_after_the_threshold(monkeypatch, clock):
    bridge.set_host_dispatch_ready(True)
    bridge.set_host_dispatch_ready(False)
    deferred = _deferred(monkeypatch, _blocked)
    clock["t"] += 121
    result = deferred.check_is_finished()
    assert result["success"] is False
    assert result["context"]["reason"] == "host_unresponsive"
    assert result["context"]["request_id"] == REQUEST_ID
    assert result["context"]["host_unresponsive_since"] == "1970-01-01T00:16:40+00:00"
    assert "inspect_job" in result["prompt"]


def test_recovery_clears_the_unresponsive_time(clock):
    bridge.set_host_dispatch_ready(False)
    assert bridge.host_unresponsive_since() == 1_000.0
    clock["t"] += 5
    bridge.set_host_dispatch_ready(False)
    assert bridge.host_unresponsive_since() == 1_000.0
    bridge.set_host_dispatch_ready(True)
    assert bridge.host_unresponsive_since() is None
