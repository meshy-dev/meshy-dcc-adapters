"""Assign a Geometry Nodes group to an object."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import assign_geometry_node_group


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_geometry_node_group`."""
    return assign_geometry_node_group(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
