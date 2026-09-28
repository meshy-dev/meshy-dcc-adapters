"""Add a Mantaflow fluid modifier to a mesh object."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._physics_ops import add_fluid_modifier


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_fluid_modifier`."""
    return add_fluid_modifier(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
