"""Get material assignments for one object."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._material_pipeline_ops import get_shader_assignment


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_shader_assignment`."""
    return get_shader_assignment(**kwargs)


if __name__ == "__main__":
    run_main(main)
