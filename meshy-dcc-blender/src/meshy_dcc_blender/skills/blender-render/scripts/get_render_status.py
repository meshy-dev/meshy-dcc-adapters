"""Report animation frame range and render state."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._render_ops import get_render_status


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_render_status`."""
    return get_render_status(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
