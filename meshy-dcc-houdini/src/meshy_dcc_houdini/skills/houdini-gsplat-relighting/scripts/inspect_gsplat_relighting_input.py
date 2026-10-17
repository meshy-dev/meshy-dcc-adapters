"""Skill entrypoint for GSplat relighting preflight."""

from gsplat_relighting import inspect_gsplat_relighting_input
from meshy_dcc_core.skill import run_main, skill_entry


@skill_entry
def main(**kwargs):
    return inspect_gsplat_relighting_input(**kwargs)


if __name__ == "__main__":
    run_main(main)
