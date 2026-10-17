"""Collect lightweight ZBrush scene metadata."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_zbrush.api import with_zbrush, zb_success


def _collect(zbc) -> dict:
    active_index = int(zbc.get_active_subtool_index())
    return {
        "active_tool_path": str(zbc.get_active_tool_path() or ""),
        "subtool_count": int(zbc.get_subtool_count()),
        "active_subtool_index": active_index,
    }


@skill_entry
@with_zbrush
def get_scene_info(**kwargs) -> dict:
    from meshy_dcc_zbrush._skill_host import run_in_zbrush  # noqa: PLC0415

    info = run_in_zbrush(_collect, "get_scene_info")
    return zb_success("ZBrush scene info", **info)


def main(**kwargs) -> dict:
    return get_scene_info(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
