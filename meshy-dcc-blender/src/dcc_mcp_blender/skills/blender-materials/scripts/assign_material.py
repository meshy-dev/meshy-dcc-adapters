"""Assign a material to a Blender object."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_blender._modeling_ops import assign_material


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_material`."""
    return assign_material(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
