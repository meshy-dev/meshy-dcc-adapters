"""Retarget pose/action data between Blender armatures."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rigging_ops import retarget_animation


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`retarget_animation`."""
    return retarget_animation(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
