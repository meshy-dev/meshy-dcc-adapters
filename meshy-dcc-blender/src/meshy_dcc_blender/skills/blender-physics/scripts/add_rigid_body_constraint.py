"""Add a rigid-body constraint to a Blender object."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._physics_ops import add_rigid_body_constraint


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_rigid_body_constraint`."""
    return add_rigid_body_constraint(**kwargs)


if __name__ == "__main__":
    run_main(main)
