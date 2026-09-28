"""List all external .blend file references (library linking)."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_assembly_ops import list_external_references


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_external_references`."""
    return list_external_references(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
