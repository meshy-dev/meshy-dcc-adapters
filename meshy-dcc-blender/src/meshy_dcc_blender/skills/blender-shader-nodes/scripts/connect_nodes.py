"""Connect two Blender node sockets."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import connect_nodes


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_nodes`."""
    return connect_nodes(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
