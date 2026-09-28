"""Typed Blender modeling entry point for uv_project."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import uv_project


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return uv_project(**kwargs)
