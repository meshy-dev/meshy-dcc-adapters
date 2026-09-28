"""Create a UV map on a Blender mesh object."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._uv_ops import create_uv_map


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_uv_map`."""
    return create_uv_map(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
