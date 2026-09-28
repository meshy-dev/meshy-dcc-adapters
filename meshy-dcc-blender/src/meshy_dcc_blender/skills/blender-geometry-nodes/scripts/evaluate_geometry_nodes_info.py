"""Evaluate a Geometry Nodes modifier graph summary."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import evaluate_geometry_nodes_info


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`evaluate_geometry_nodes_info`."""
    return evaluate_geometry_nodes_info(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
