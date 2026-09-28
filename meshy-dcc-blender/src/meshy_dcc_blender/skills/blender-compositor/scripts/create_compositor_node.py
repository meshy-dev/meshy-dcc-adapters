"""Create a compositor node."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._compositor_ops import create_compositor_node


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_compositor_node`."""
    return create_compositor_node(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
