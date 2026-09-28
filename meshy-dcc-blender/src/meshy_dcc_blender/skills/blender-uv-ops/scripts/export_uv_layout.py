"""Read source UV data without changing Blender context."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._uv_quality import export_uv_layout


@skill_entry
def main(**kwargs) -> dict:
    return export_uv_layout(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
