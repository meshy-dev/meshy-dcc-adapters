"""Rename a custom property on a Blender object."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._attributes_ops import rename_attribute


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rename_attribute`."""
    return rename_attribute(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
