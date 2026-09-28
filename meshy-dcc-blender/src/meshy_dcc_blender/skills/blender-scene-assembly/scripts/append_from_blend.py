"""Append data blocks from an external .blend file."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_assembly_ops import append_from_blend


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`append_from_blend`."""
    return append_from_blend(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
