"""Maya safe stop: matching instance, saved scene or the user's consent to discard."""

import threading
import types
from unittest.mock import MagicMock

import pytest

from meshy_dcc_maya import _safe_stop
from meshy_dcc_maya._safe_stop import handle_stop_request, stop_if_saved


def _cmds(modified):
    cmds = MagicMock()
    cmds.file.return_value = modified
    return cmds


def test_stop_needs_matching_instance_and_a_saved_scene_or_consent():
    cmds = _cmds(modified=True)

    def decide(body):
        return handle_stop_request(body, "inst-1", lambda discard: stop_if_saved(cmds, discard))

    assert decide({"instance_id": "inst-2", "discard_unsaved": True})[1]["reason"] == "instance_mismatch"
    status, reply = decide({"instance_id": "inst-1"})
    assert (status, reply["reason"]) == (409, "unsaved_changes")
    cmds.evalDeferred.assert_not_called()
    assert decide({"instance_id": "inst-1", "discard_unsaved": True}) == (202, {"stopping": True})
    cmds.evalDeferred.assert_called_once()


def test_saved_scene_stops_without_consent_and_quits_with_force():
    cmds = _cmds(modified=False)
    assert handle_stop_request({"instance_id": "a"}, "a", lambda d: stop_if_saved(cmds, d)) == (202, {"stopping": True})
    quit_later = cmds.evalDeferred.call_args[0][0]
    quit_later()
    cmds.quit.assert_called_once_with(force=True)


def test_unanswered_check_reads_as_unsaved():
    def stuck(_discard):
        raise TimeoutError("no answer")

    status, reply = handle_stop_request({"instance_id": "a"}, "a", stuck)
    assert (status, reply["reason"]) == (409, "unsaved_state_unknown")


def test_late_main_thread_call_does_nothing_after_timeout(monkeypatch):
    release = threading.Event()
    ran = []

    def execute_later(func):
        release.wait(5)
        return func()

    maya = types.ModuleType("maya")
    maya.utils = types.SimpleNamespace(executeInMainThreadWithResult=execute_later)
    monkeypatch.setitem(__import__("sys").modules, "maya", maya)
    monkeypatch.setitem(__import__("sys").modules, "maya.utils", maya.utils)

    with pytest.raises(TimeoutError):
        _safe_stop.run_on_main_thread(lambda: ran.append(1) or True, timeout=0.05)
    release.set()
    for thread in threading.enumerate():
        if thread.name == "meshy-dcc-safe-stop-check":
            thread.join(5)
    assert ran == []


def test_only_start_instance_launches_advertise_safe_stop(monkeypatch):
    monkeypatch.delenv(_safe_stop.START_OPERATION_ENV, raising=False)
    server = MagicMock()
    _safe_stop.attach_safe_stop(server)
    server._handle.update_gateway_metadata.assert_not_called()
