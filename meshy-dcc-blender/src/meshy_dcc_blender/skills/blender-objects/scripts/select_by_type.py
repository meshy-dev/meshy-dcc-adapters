"""Select Blender objects by type."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_ops import select_by_type


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`select_by_type`."""
    return select_by_type(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
