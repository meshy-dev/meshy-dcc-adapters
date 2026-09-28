"""Disconnect compositor node links."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._compositor_ops import disconnect_compositor_nodes


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`disconnect_compositor_nodes`."""
    return disconnect_compositor_nodes(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
