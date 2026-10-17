"""Safe stop quits Painter only when nothing is unsaved or the caller agreed to discard it."""

from __future__ import annotations

from meshy_dcc_substance3d_painter import _safe_stop


class _Project:
    def __init__(self, open_=True, dirty=False, broken=False):
        self._open, self._dirty, self._broken = open_, dirty, broken

    def is_open(self):
        return self._open

    def needs_saving(self):
        if self._broken:
            raise RuntimeError("no state")
        return self._dirty

    def file_path(self):
        return "/projects/orb.spp"

    def name(self):
        return "orb"


def _stop(project, body, instance_id="abc"):
    quits = []

    def run_on_main(discard):
        return _safe_stop.stop_if_saved(project, discard, lambda: quits.append(True))

    status, reply = _safe_stop.handle_stop_request(body, instance_id, run_on_main)
    return status, reply, bool(quits)


def test_clean_or_closed_project_quits():
    assert _stop(_Project(dirty=False), {"instance_id": "abc"})[::2] == (202, True)
    assert _stop(_Project(open_=False), {"instance_id": "abc"})[::2] == (202, True)


def test_unsaved_or_unknown_state_is_refused_without_consent():
    for project in (_Project(dirty=True), _Project(broken=True)):
        status, reply, quit_ = _stop(project, {"instance_id": "abc"})
        assert (status, reply["reason"], quit_) == (409, "unsaved_changes", False)
    assert _stop(_Project(dirty=True), {"instance_id": "abc"})[1]["unsaved"] == ["/projects/orb.spp"]


def test_discard_unsaved_quits_a_dirty_project():
    assert _stop(_Project(dirty=True), {"instance_id": "abc", "discard_unsaved": True})[::2] == (202, True)


def test_wrong_instance_is_refused_before_touching_painter():
    status, reply, quit_ = _stop(_Project(broken=True), {"instance_id": "other", "discard_unsaved": True})
    assert (status, reply["reason"], quit_) == (409, "instance_mismatch", False)
