"""Create a revision-pinned Geometry Nodes interface socket."""

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._geometry_interface_ops import create_geometry_node_socket


@skill_entry
def main(**kwargs) -> dict:
    return create_geometry_node_socket(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
