"""Set multiple Principled BSDF inputs on a material."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._node_graph_ops import set_principled_inputs


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_principled_inputs`."""
    return set_principled_inputs(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
