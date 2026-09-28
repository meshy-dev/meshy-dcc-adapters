"""Export Blender data to Alembic."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._interchange_ops import export_alembic


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_alembic`."""
    return export_alembic(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
