"""Mirror edit bones in a Blender armature."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rigging_ops import mirror_bones


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`mirror_bones`."""
    return mirror_bones(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
