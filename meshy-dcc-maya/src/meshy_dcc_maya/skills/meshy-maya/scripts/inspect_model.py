"""meshy-maya inspect_model; the work is in meshy_dcc_maya.meshy_import."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry, skill_error


@skill_entry
def main(**kwargs) -> dict:
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    from meshy_dcc_maya.meshy_import import inspect_model  # noqa: PLC0415

    return inspect_model(cmds, **kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
