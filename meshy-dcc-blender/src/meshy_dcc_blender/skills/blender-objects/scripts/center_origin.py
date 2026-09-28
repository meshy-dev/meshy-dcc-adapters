"""Center or move a Blender object's origin."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_ops import center_origin


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`center_origin`."""
    return center_origin(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
