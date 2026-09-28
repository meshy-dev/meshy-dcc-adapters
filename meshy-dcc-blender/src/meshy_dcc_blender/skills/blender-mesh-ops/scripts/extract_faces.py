"""Extract selected face indices from a Blender mesh."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._mesh_ops import extract_faces


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`extract_faces`."""
    return extract_faces(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
