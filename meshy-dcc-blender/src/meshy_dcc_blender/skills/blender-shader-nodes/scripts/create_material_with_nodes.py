"""Create a node-based Blender material."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import create_material_with_nodes


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_material_with_nodes`."""
    return create_material_with_nodes(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
