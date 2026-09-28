"""Create or update a Blender driver."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rigging_ops import set_driver


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_driver`."""
    return set_driver(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
