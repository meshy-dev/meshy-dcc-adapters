"""Import a USD file into Blender."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._interchange_ops import import_usd


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`import_usd`."""
    return import_usd(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
