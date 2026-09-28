"""Typed Blender modeling entry point for group_parent."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import group_parent


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return group_parent(**kwargs)
