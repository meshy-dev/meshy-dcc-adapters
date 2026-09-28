"""Get a custom property value by name from a Blender object."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._attributes_ops import get_attribute


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_attribute`."""
    return get_attribute(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
