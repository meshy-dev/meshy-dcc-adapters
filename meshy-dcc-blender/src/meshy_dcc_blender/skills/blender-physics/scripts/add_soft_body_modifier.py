"""Add a soft-body modifier to a Blender mesh object."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._physics_ops import add_soft_body_modifier


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_soft_body_modifier`."""
    return add_soft_body_modifier(**kwargs)


if __name__ == "__main__":
    run_main(main)
