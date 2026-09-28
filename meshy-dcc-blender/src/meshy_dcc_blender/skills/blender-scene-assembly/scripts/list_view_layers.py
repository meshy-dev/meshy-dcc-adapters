"""List view layers in a scene."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_assembly_ops import list_view_layers


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_view_layers`."""
    return list_view_layers(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
