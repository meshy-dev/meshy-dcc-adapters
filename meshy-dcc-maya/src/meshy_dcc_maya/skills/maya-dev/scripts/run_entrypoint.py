"""Run a Python entrypoint from an attached Maya tool project."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_maya import _dev_session


@skill_entry
def main(**kwargs) -> dict:
    return _dev_session.run_entrypoint(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
