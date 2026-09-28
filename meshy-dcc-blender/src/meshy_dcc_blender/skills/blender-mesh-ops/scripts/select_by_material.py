"""Select Blender mesh faces by material name."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._mesh_ops import select_by_material


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`select_by_material`."""
    return select_by_material(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
