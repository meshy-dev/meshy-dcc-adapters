"""Bake Blender ambient occlusion."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._material_pipeline_ops import bake_ambient_occlusion


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_ambient_occlusion`."""
    return bake_ambient_occlusion(**kwargs)


if __name__ == "__main__":
    run_main(main)
