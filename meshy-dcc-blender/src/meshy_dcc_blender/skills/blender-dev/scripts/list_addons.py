"""List Blender add-ons and development status."""

from __future__ import annotations

from meshy_dcc_core.skill import run_main, skill_entry

from meshy_dcc_blender._dev_ops import list_addons


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_addons`."""
    return list_addons(**kwargs)


if __name__ == "__main__":
    run_main(main)
