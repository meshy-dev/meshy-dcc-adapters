"""List sockets on a Blender node."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import list_node_sockets


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_node_sockets`."""
    return list_node_sockets(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
