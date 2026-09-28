"""Remove a rigid-body constraint from a Blender object."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._physics_ops import remove_rigid_body_constraint


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_rigid_body_constraint`."""
    return remove_rigid_body_constraint(**kwargs)


if __name__ == "__main__":
    run_main(main)
