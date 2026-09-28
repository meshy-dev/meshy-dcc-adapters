"""Get the current Blender object selection."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._scene_ops import get_selection


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_selection`."""
    return get_selection(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
