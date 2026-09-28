"""Set extrapolation on an action's fcurves."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._nla_ops import set_action_fcurve_extrapolation


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_action_fcurve_extrapolation`."""
    return set_action_fcurve_extrapolation(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
