"""Bake Blender animation by inserting sampled keyframes."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._animation_ops import bake_animation


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_animation`."""
    return bake_animation(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
