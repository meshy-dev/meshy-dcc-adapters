"""Start an optional debugpy server for Blender development."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._dev_ops import start_debug_server


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`start_debug_server`."""
    return start_debug_server(**kwargs)


if __name__ == "__main__":
    run_main(main)
