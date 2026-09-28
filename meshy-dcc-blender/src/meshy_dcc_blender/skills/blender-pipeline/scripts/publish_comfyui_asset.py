"""Publish a Blender GLB revision for official ComfyUI workflows."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._comfyui_publish_ops import publish_comfyui_asset


@skill_entry
def main(**kwargs) -> dict:
    return publish_comfyui_asset(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
