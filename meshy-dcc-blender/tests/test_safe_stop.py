"""Blender safe stop refuses unless the user agreed to discard unsaved work."""

from dcc_mcp_blender._safe_stop import handle_stop_request


def test_stop_needs_matching_instance_and_discard_consent():
    quits = []

    def decide(body):
        return handle_stop_request(body, "inst-1", lambda: quits.append(1))

    assert decide({"instance_id": "inst-2", "discard_unsaved": True})[1]["reason"] == "instance_mismatch"
    status, reply = decide({"instance_id": "inst-1"})
    assert (status, reply["reason"]) == (409, "unsaved_state_unknown")
    assert quits == []
    assert decide({"instance_id": "inst-1", "discard_unsaved": True}) == (202, {"stopping": True})
    assert quits == [1]
