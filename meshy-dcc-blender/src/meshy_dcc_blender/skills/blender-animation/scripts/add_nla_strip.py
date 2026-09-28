"""Place an action on an NLA track as a strip."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._nla_ops import add_nla_strip


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_nla_strip`."""
    return add_nla_strip(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
