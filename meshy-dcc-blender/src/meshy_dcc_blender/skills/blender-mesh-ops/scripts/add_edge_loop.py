"""Typed Blender modeling entry point for add_edge_loop."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import add_edge_loop


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return add_edge_loop(**kwargs)
