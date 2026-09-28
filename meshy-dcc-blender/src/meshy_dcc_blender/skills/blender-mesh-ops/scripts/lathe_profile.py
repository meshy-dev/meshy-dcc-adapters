"""Typed Blender modeling entry point for lathe_profile."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._modeling_ops import lathe_profile


@skill_entry
def main(**kwargs) -> dict:
    """Run the bounded modeling operation."""
    return lathe_profile(**kwargs)
