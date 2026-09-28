"""List poses saved on Blender armatures."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._pose_ops import list_poses


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_poses`."""
    return list_poses(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
