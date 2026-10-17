"""Attach a local Maya tool development project to the live session."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_maya import _dev_session


@skill_entry
def main(**kwargs) -> dict:
    return _dev_session.attach_project(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
