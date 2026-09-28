"""Update Mantaflow fluid settings."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._physics_ops import set_fluid_settings


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_fluid_settings`."""
    return set_fluid_settings(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
