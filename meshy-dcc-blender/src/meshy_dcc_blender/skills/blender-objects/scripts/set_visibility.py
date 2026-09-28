"""Set Blender object visibility."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_ops import set_visibility


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_visibility`."""
    return set_visibility(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
