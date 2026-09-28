"""Group Blender lights into a rig collection."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._light_rig_ops import group_lights


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`group_lights`."""
    return group_lights(**kwargs)


if __name__ == "__main__":
    run_main(main)
