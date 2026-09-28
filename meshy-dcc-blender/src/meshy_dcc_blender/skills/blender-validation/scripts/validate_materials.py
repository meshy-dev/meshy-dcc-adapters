"""Validate Blender material assignments."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._asset_pipeline_ops import validate_materials


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`validate_materials`."""
    return validate_materials(**kwargs)


if __name__ == "__main__":
    run_main(main)
