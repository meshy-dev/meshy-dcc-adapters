"""Houdini safe stop refuses while the scene is unsaved unless the user agreed to discard it."""

from types import SimpleNamespace

from meshy_dcc_houdini._safe_stop import handle_stop_request, stop_if_saved


def _hou(dirty):
    def has_unsaved():
        if dirty is None:
            raise RuntimeError("no HOM")
        return dirty

    return SimpleNamespace(isUIAvailable=lambda: True, hipFile=SimpleNamespace(hasUnsavedChanges=has_unsaved))


def test_stop_needs_matching_instance_and_a_saved_scene_or_consent():
    exits = []

    def decide(body, dirty):
        return handle_stop_request(
            body, "inst-1", lambda discard: stop_if_saved(_hou(dirty), discard, lambda: exits.append(1))
        )

    assert decide({"instance_id": "inst-2", "discard_unsaved": True}, False)[1]["reason"] == "instance_mismatch"
    status, reply = decide({"instance_id": "inst-1"}, True)
    assert (status, reply["reason"]) == (409, "unsaved_changes")
    assert decide({"instance_id": "inst-1"}, None)[1]["reason"] == "unsaved_state_unknown"
    assert exits == []
    assert decide({"instance_id": "inst-1"}, False) == (202, {"stopping": True})
    assert decide({"instance_id": "inst-1", "discard_unsaved": True}, True) == (202, {"stopping": True})
    assert exits == [1, 1]
