"""Remove a view layer from a scene."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_assembly_ops import remove_view_layer


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_view_layer`."""
    return remove_view_layer(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
