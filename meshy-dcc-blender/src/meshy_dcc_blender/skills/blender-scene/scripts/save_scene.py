"""Save the current Blender scene, then read the saved file back."""

from __future__ import annotations

import os
import stat
import time
from typing import Optional

from meshy_dcc_blender._modeling_common import operator_finished
from meshy_dcc_core.skill import skill_entry, skill_error, skill_exception, skill_success

# File times come from the filesystem's own granularity (2 s on FAT) and clock (a
# share's, over a network), so a file this much older than the call is not this save.
_MTIME_SLACK_SECS = 2.0


def _read_back(path: str, started: float):
    """Return ``(stat, None)`` for a fresh, nonempty regular file, else ``(None, reason)``."""
    try:
        info = os.stat(path)
    except OSError as exc:
        return None, f"it cannot be read back: {exc}"
    if not stat.S_ISREG(info.st_mode) or info.st_size <= 0:
        return None, "it is not a nonempty regular file"
    if info.st_mtime < started - _MTIME_SLACK_SECS:
        return None, "its modification time predates this save"
    return info, None


def _unverified(error: str, **context) -> dict:
    """A save that ran but could not be confirmed: its effect on disk is unknown."""
    return skill_error(
        "Failed to save scene",
        error,
        mutation_applied=None,
        prompt="Inspect the scene path and the file before retrying. The save was not retried or rolled back.",
        **context,
    )


def save_scene(filepath: Optional[str] = None) -> dict:
    """Save the current Blender scene and report success only after reading it back.

    Success needs the operator to report FINISHED and the path Blender then reports
    for the scene to be a fresh, nonempty regular file. A file that was already
    there never counts. It does not prove the content is intact: reopen to check.

    Args:
        filepath: Optional path to save the scene to. If None, saves to the
            current file path. If the scene has never been saved, this is required.

    Returns:
        ActionResultModel dict.
    """
    attempted = False
    try:
        import bpy

        if not filepath and not bpy.data.filepath:
            return skill_error(
                "No filepath specified",
                "The scene has not been saved yet. Please provide a filepath.",
            )
        started = time.time()
        attempted = True
        if filepath:
            result = bpy.ops.wm.save_as_mainfile(filepath=filepath)
        else:
            result = bpy.ops.wm.save_mainfile()
        if not operator_finished(result):
            return _unverified(
                "Blender did not report FINISHED; a file already at the path is not proof of a save.",
                operator_result=sorted(result) if isinstance(result, set) else repr(result),
            )
        # Blender sets the scene path to where it wrote the file, which may differ from
        # the request (it appends .blend), so that is the path to read back and report.
        saved_path = bpy.data.filepath
        if not saved_path:
            return _unverified("Blender reports no saved scene path after the save.")
        info, problem = _read_back(saved_path, started)
        if problem:
            return _unverified(f"The saved file {saved_path} failed the readback: {problem}.", filepath=saved_path)
        return skill_success(
            f"Scene saved to {saved_path}",
            filepath=saved_path,
            file_size_bytes=info.st_size,
            verified=True,
            postcondition={
                "method": "finished_operator_fresh_nonempty_file",
                "path": saved_path,
                "size_bytes": info.st_size,
                "mtime": info.st_mtime,
            },
            prompt="Operator FINISHED and the saved file was read back. Reopen it if its content must be confirmed.",
        )
    except ImportError:
        return skill_error("Blender not available", "bpy could not be imported")
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to save scene",
            mutation_applied=None if attempted else False,
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`save_scene`."""
    return save_scene(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
