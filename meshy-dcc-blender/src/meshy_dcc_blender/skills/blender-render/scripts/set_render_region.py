"""Enable and configure border rendering."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._render_ops import set_render_region


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_region`."""
    return set_render_region(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
