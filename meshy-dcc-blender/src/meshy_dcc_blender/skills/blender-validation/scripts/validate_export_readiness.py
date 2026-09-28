"""Validate Blender export readiness."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._asset_pipeline_ops import validate_export_readiness


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`validate_export_readiness`."""
    return validate_export_readiness(**kwargs)


if __name__ == "__main__":
    run_main(main)
