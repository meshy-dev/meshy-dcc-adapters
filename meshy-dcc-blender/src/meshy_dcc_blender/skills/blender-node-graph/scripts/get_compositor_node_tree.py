"""Return the compositor node tree for the current scene."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import get_compositor_node_tree


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_compositor_node_tree`."""
    return get_compositor_node_tree(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
