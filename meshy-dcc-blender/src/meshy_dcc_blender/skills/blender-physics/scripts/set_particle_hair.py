"""Switch a particle system between emitter and hair mode."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._physics_ops import set_particle_hair


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_particle_hair`."""
    return set_particle_hair(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
