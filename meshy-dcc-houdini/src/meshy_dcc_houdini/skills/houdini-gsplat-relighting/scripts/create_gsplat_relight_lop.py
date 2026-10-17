"""Skill entrypoint for Solaris GSplat relighting."""

from gsplat_relighting import create_gsplat_relight_lop
from meshy_dcc_core.skill import run_main, skill_entry


@skill_entry
def main(**kwargs):
    return create_gsplat_relight_lop(**kwargs)


if __name__ == "__main__":
    run_main(main)
