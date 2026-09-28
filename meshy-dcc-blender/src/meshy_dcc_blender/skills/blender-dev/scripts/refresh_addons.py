"""Rescan add-on paths so newly installed add-ons appear."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._dev_ops import refresh_addons


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`refresh_addons`."""
    return refresh_addons(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
