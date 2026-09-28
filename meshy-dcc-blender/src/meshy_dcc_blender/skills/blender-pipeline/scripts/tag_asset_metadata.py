"""Tag Blender object asset metadata."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._asset_pipeline_ops import tag_asset_metadata


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`tag_asset_metadata`."""
    return tag_asset_metadata(**kwargs)


if __name__ == "__main__":
    run_main(main)
