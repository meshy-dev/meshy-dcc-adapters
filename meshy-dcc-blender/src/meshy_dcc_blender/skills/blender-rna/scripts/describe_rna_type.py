"""Describe bounded live Blender RNA property metadata."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._rna_query import describe_rna_type


@skill_entry
def main(**kwargs) -> dict:
    """Delegate to the host-specific RNA query implementation."""
    return describe_rna_type(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
