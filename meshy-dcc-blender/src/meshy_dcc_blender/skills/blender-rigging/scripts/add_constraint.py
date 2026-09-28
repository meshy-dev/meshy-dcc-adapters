"""Add a Blender object constraint."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rigging_ops import add_constraint


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_constraint`."""
    return add_constraint(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
