"""Mirror a Blender mesh with a Mirror modifier."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._mesh_ops import mirror_mesh


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`mirror_mesh`."""
    return mirror_mesh(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
