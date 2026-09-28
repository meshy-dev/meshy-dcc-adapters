"""Capture structured Blender UI metadata."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._dev_ops import capture_ui_snapshot


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`capture_ui_snapshot`."""
    return capture_ui_snapshot(**kwargs)


if __name__ == "__main__":
    run_main(main)
