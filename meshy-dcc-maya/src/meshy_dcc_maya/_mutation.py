"""Small fail-closed helpers for verified Maya scene mutations."""

from __future__ import annotations

import uuid


def node_uuid(cmds, node):
    # type: (...) -> str
    """Return the one exact Maya UUID for ``node`` or fail closed."""
    values = [str(value) for value in (cmds.ls(node, uuid=True) or [])]
    if len(values) != 1 or not values[0]:
        raise RuntimeError("Maya did not return one exact node UUID")
    return values[0]


def uuid_inventory(cmds):
    # type: (...) -> set
    """Snapshot all Maya UUIDs for exact creation and rollback proofs."""
    return {str(value) for value in (cmds.ls(uuid=True) or [])}


def shape_uuids(cmds, transform):
    # type: (...) -> set
    """Return UUIDs for the transform's non-intermediate shapes."""
    shapes = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True) or []
    return {node_uuid(cmds, shape) for shape in shapes}


class MayaUndoChunk:
    """Own one Maya undo chunk and emit a structured rollback receipt.

    Maya only records an undo item when an undoable command ran inside the
    chunk, so an empty chunk has no entry of its own and ``undo()`` would pop
    the user's previous edit. Each chunk therefore gets a unique name, and
    ``rollback`` calls ``undo()`` only when that exact name is the top undo
    item. Anything else (empty chunk, a foreign edit on top, a host that cannot
    report undo names) undoes nothing and is reported as not verified.
    """

    def __init__(self, cmds, name):
        # type: (...) -> None
        self._cmds = cmds
        self._name = name
        self._chunk_name = "{}__{}".format(name, uuid.uuid4().hex)
        self._open = False

    def begin(self):
        # type: (...) -> None
        if not bool(self._cmds.undoInfo(query=True, state=True)):
            raise RuntimeError("Maya undo must be enabled for this verified mutation")
        self._cmds.undoInfo(openChunk=True, chunkName=self._chunk_name)
        self._open = True

    def _close(self):
        # type: (...) -> None
        if self._open:
            self._cmds.undoInfo(closeChunk=True)
            self._open = False

    def commit(self):
        # type: (...) -> None
        self._close()

    def _owns_top_undo_item(self):
        # type: (...) -> bool
        try:
            top = self._cmds.undoInfo(query=True, undoName=True)
        except Exception:
            return False
        return isinstance(top, str) and top == self._chunk_name

    def rollback(self, verifier):
        # type: (...) -> dict
        """Undo this chunk only, then verify the caller-provided pre-state contract."""
        receipt = {"rollback_attempted": False, "rollback_verified": False}
        try:
            self._close()
            if not self._owns_top_undo_item():
                receipt["rollback_skipped_reason"] = "undo_item_not_owned"
                return receipt
            receipt["rollback_attempted"] = True
            self._cmds.undo()
            receipt["rollback_verified"] = bool(verifier())
        except Exception as exc:
            receipt["rollback_verified"] = False
            receipt["rollback_error_type"] = type(exc).__name__
        return receipt
