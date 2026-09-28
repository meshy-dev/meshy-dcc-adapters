"""Typed Blender modeling entry point for set_pivot."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import set_pivot


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return set_pivot(**kwargs)
