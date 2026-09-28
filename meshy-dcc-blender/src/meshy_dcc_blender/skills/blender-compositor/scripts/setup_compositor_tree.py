"""Enable the compositor and optionally build a starter node tree."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._compositor_ops import setup_compositor_tree


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`setup_compositor_tree`."""
    return setup_compositor_tree(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
