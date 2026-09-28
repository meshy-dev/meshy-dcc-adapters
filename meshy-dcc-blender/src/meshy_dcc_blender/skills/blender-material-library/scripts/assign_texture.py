"""Assign an image texture to a material."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._material_pipeline_ops import assign_texture


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_texture`."""
    return assign_texture(**kwargs)


if __name__ == "__main__":
    run_main(main)
