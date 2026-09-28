"""Merge nearby vertices on a Blender mesh."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._mesh_ops import merge_vertices


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`merge_vertices`."""
    return merge_vertices(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
