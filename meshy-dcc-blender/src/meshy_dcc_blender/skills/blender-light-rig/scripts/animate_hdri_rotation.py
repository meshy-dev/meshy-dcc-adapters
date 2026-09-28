"""Animate Blender HDRI rotation for LookDev lighting changes."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._light_rig_ops import animate_hdri_rotation


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`animate_hdri_rotation`."""
    return animate_hdri_rotation(**kwargs)


if __name__ == "__main__":
    run_main(main)
