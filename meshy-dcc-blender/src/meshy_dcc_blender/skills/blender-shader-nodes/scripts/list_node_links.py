"""List Blender node links."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import list_node_links


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_node_links`."""
    return list_node_links(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
