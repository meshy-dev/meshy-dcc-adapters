"""Read bounded named modifier values without traversing links."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rna_query import get_modifier_values


@skill_entry
def main(**kwargs) -> dict:
    """Delegate to the host-specific RNA query implementation."""
    return get_modifier_values(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
