"""Get UV statistics for a Blender mesh object."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._uv_ops import get_uv_info


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_uv_info`."""
    return get_uv_info(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
