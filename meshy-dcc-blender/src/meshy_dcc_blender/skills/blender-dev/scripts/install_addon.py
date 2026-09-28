"""Install a Blender add-on from a .py file or a .zip bundle."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._dev_ops import install_addon


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`install_addon`."""
    return install_addon(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
