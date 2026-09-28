"""List the actions available for animation."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._nla_ops import list_animation_actions


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_animation_actions`."""
    return list_animation_actions(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
