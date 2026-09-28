"""Inspect a bounded Geometry Nodes group interface."""

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._geometry_interface_ops import inspect_geometry_node_interface


@skill_entry
def main(**kwargs) -> dict:
    return inspect_geometry_node_interface(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
