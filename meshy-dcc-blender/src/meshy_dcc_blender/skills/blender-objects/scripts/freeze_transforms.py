"""Freeze Blender object transforms."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_ops import freeze_transforms


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`freeze_transforms`."""
    return freeze_transforms(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
