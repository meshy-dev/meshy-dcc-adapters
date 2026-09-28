"""Typed Blender modeling entry point for array_instances."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import array_instances


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return array_instances(**kwargs)
