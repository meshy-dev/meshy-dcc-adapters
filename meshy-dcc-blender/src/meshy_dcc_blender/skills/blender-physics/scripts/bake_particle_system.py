"""Bake or free the point cache of one particle system."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._physics_ops import bake_particle_system


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_particle_system`."""
    return bake_particle_system(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
