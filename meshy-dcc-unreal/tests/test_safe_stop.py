"""Consent-gated safe stop: Unreal quits without a save prompt, so unsaved work must block it."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from meshy_dcc_unreal._safe_stop import handle_stop_request, stop_if_saved


class Package:
    def __init__(self, name: str) -> None:
        self.name = name

    def get_name(self) -> str:
        return self.name


def fake_unreal(maps=(), content=(), broken=False):
    calls = []

    def dirty_maps():
        if broken:
            raise RuntimeError("no dirty-package API")
        return [Package(name) for name in maps]

    return calls, SimpleNamespace(
        EditorLoadingAndSavingUtils=SimpleNamespace(
            get_dirty_map_packages=dirty_maps,
            get_dirty_content_packages=lambda: [Package(name) for name in content],
        ),
        SystemLibrary=SimpleNamespace(quit_editor=lambda: calls.append("quit")),
    )


@pytest.mark.parametrize(
    ("state", "discard", "blocked", "quit"),
    [
        ({}, False, [], True),
        ({"maps": ["/Game/Maps/Handoff"]}, False, ["/Game/Maps/Handoff"], False),
        ({"content": ["/Game/Meshy/Orb/Orb"]}, False, ["/Game/Meshy/Orb/Orb"], False),
        ({"broken": True}, False, None, False),
        ({"maps": ["/Game/Maps/Handoff"]}, True, [], True),
        ({"broken": True}, True, [], True),
    ],
)
def test_stop_quits_only_saved_or_consented_editors(state, discard, blocked, quit):
    calls, unreal = fake_unreal(**state)
    assert stop_if_saved(unreal, discard) == blocked
    assert calls == (["quit"] if quit else [])


def test_stop_request_checks_the_instance_and_reports_what_is_unsaved():
    seen = []

    def run_on_editor(discard):
        seen.append(discard)
        return [] if discard else ["/Game/Maps/Handoff"]

    assert handle_stop_request({"instance_id": "other"}, "i", run_on_editor)[1]["reason"] == "instance_mismatch"
    assert seen == []

    code, reply = handle_stop_request({"instance_id": "i"}, "i", run_on_editor)
    assert (code, reply["reason"], reply["unsaved"]) == (409, "unsaved_changes", ["/Game/Maps/Handoff"])

    # Only a literal true counts as consent.
    handle_stop_request({"instance_id": "i", "discard_unsaved": "yes"}, "i", run_on_editor)
    assert handle_stop_request({"instance_id": "i", "discard_unsaved": True}, "i", run_on_editor) == (
        202,
        {"stopping": True},
    )
    assert seen == [False, False, True]
