"""Read the Unreal Editor session: process, project, level and unsaved packages."""

from __future__ import annotations

import os

from _meshy import dirty_packages, level_path, project_dir
from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unreal.__version__ import __version__


@skill_entry
def session(**kwargs) -> dict:
    import unreal  # noqa: PLC0415

    dirty = dirty_packages(unreal)
    unsaved = None if dirty is None else dirty[0]
    level = level_path(unreal)
    return skill_success(
        "Read Unreal Editor session",
        host_pid=os.getpid(),
        workspace=project_dir(unreal),
        project_file=os.path.realpath(unreal.Paths.get_project_file_path()),
        engine_version=str(unreal.SystemLibrary.get_engine_version()),
        adapter_version=__version__,
        level=level,
        level_in_project=bool(level and level.startswith("/Game/")),
        dirty=None if unsaved is None else bool(unsaved),
        unsaved=unsaved,
        # Engine content that got dirty on its own; never save it.
        engine_unsaved=None if dirty is None else dirty[1],
    )
