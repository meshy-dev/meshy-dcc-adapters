"""Add a shape key to a Blender mesh."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rigging_ops import add_shape_key


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_shape_key`."""
    return add_shape_key(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
