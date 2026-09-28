"""Turn AOV passes on or off for a view layer."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._render_ops import set_view_layer_passes


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_view_layer_passes`."""
    return set_view_layer_passes(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
