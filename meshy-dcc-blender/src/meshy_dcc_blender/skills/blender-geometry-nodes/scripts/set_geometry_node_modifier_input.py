"""Set an exposed Geometry Nodes modifier input."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import set_geometry_node_modifier_input


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_geometry_node_modifier_input`."""
    return set_geometry_node_modifier_input(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
