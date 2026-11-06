"""Unit tests for fail-closed Maya mutation receipts."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from conftest import wire_named_undo_queue

from meshy_dcc_maya._mutation import MayaUndoChunk


def _open_chunk_names(cmds):
    return [call[1]["chunkName"] for call in cmds.undoInfo.call_args_list if call[1].get("openChunk")]


def test_undo_chunk_refuses_mutation_when_maya_undo_is_disabled():
    cmds = MagicMock()
    wire_named_undo_queue(cmds, undo_enabled=False)
    transaction = MayaUndoChunk(cmds, "verified_mutation")

    with pytest.raises(RuntimeError, match="undo must be enabled"):
        transaction.begin()

    # ``call.kwargs`` was added after Python 3.7. Maya 2022's unittest.mock
    # otherwise treats that attribute access as another truthy mock call.
    assert not any(call[1].get("openChunk") for call in cmds.undoInfo.call_args_list)

    receipt = transaction.rollback(lambda: True)

    # No chunk was opened, so there is no undo item to own; a truthy verifier
    # must not turn that into a verified rollback.
    assert receipt == {
        "rollback_attempted": False,
        "rollback_verified": False,
        "rollback_skipped_reason": "undo_item_not_owned",
    }
    cmds.undo.assert_not_called()


def test_undo_chunk_surfaces_incomplete_rollback_without_exception_text():
    cmds = MagicMock()
    wire_named_undo_queue(cmds)
    cmds.undo.side_effect = RuntimeError("local scene detail must not leak")
    transaction = MayaUndoChunk(cmds, "verified_mutation")
    transaction.begin()

    receipt = transaction.rollback(lambda: True)

    assert receipt == {
        "rollback_attempted": True,
        "rollback_verified": False,
        "rollback_error_type": "RuntimeError",
    }
    assert "local scene detail" not in str(receipt)
    # Each chunk gets a unique name so a foreign chunk that reuses the readable
    # name is never mistaken for ours.
    names = _open_chunk_names(cmds)
    assert len(names) == 1 and names[0].startswith("verified_mutation__")
    cmds.undoInfo.assert_any_call(closeChunk=True)


def test_undo_chunk_undoes_when_its_own_chunk_is_the_top_undo_item():
    cmds = wire_named_undo_queue(MagicMock())
    transaction = MayaUndoChunk(cmds, "verified_mutation")
    transaction.begin()

    receipt = transaction.rollback(lambda: True)

    assert receipt == {"rollback_attempted": True, "rollback_verified": True}
    cmds.undo.assert_called_once_with()


def test_undo_chunk_does_not_undo_the_previous_edit_when_the_chunk_recorded_nothing():
    cmds = MagicMock()
    # Maya records no item for a chunk without undoable commands, so the top
    # item is still the user's own earlier edit.
    cmds.undoInfo.side_effect = lambda **kw: "user edit" if kw.get("undoName") else True
    transaction = MayaUndoChunk(cmds, "verified_mutation")
    transaction.begin()

    receipt = transaction.rollback(lambda: True)

    assert receipt == {
        "rollback_attempted": False,
        "rollback_verified": False,
        "rollback_skipped_reason": "undo_item_not_owned",
    }
    cmds.undo.assert_not_called()


def test_undo_chunk_fails_closed_when_the_host_cannot_report_undo_names():
    cmds = MagicMock()
    cmds.undoInfo.return_value = True
    transaction = MayaUndoChunk(cmds, "verified_mutation")
    transaction.begin()

    receipt = transaction.rollback(lambda: True)

    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False
    cmds.undo.assert_not_called()
