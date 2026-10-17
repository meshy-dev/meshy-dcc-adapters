"""Skill entrypoint for Copernicus GSplat rasterization."""

from gsplat_relighting import create_gsplat_copernicus_raster
from meshy_dcc_core.skill import run_main, skill_entry


@skill_entry
def main(**kwargs):
    return create_gsplat_copernicus_raster(**kwargs)


if __name__ == "__main__":
    run_main(main)
