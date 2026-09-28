"""Export the current Blender scene or selected objects to OBJ."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_blender._interchange_ops import export_obj


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_obj`."""
    return export_obj(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
