"""Typed Blender modeling entry point for bevel_edges."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import bevel_edges


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return bevel_edges(**kwargs)
