"""Set Blender scene color management."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._material_pipeline_ops import set_color_management


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_color_management`."""
    return set_color_management(**kwargs)


if __name__ == "__main__":
    run_main(main)
