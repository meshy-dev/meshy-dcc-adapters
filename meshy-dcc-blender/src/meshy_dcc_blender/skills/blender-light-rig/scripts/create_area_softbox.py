"""Create a Blender area softbox."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._light_rig_ops import create_area_softbox


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_area_softbox`."""
    return create_area_softbox(**kwargs)


if __name__ == "__main__":
    run_main(main)
