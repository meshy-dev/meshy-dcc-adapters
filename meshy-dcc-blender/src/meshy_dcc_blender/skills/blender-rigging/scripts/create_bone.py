"""Create an edit bone in a Blender armature."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rigging_ops import create_bone


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_bone`."""
    return create_bone(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
