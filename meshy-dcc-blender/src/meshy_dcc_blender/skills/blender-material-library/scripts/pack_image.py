"""Embed an image into the .blend file."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._image_light_ops import pack_image


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`pack_image`."""
    return pack_image(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
