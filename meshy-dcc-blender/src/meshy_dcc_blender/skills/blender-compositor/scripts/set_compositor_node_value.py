"""Set a compositor node input socket value."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._compositor_ops import set_compositor_node_value


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_compositor_node_value`."""
    return set_compositor_node_value(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
