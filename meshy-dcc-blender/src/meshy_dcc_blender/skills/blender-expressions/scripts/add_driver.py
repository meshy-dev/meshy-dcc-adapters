"""Add a driver to a Blender object property."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._expressions_ops import add_driver


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_driver`."""
    return add_driver(**kwargs)


if __name__ == "__main__":
    run_main(main)
