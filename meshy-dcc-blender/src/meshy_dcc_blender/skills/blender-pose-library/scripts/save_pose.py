"""Save the current pose of a Blender armature."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._pose_ops import save_pose


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`save_pose`."""
    return save_pose(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
