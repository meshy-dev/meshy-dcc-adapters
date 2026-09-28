"""Transfer Blender texture maps between meshes."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._material_pipeline_ops import transfer_maps


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`transfer_maps`."""
    return transfer_maps(**kwargs)


if __name__ == "__main__":
    run_main(main)
