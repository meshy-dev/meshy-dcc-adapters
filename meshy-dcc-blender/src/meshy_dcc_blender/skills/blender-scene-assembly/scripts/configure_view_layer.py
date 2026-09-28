"""Configure Blender view-layer passes and collection visibility."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_assembly_ops import configure_view_layer


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`configure_view_layer`."""
    return configure_view_layer(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
