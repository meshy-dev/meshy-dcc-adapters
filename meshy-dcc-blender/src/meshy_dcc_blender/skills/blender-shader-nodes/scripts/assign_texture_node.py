"""Assign an image texture node to a material graph."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import assign_texture_node


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_texture_node`."""
    return assign_texture_node(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
