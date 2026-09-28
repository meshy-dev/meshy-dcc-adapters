"""Write a packed image out to disk and stop embedding it."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._image_light_ops import unpack_image


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unpack_image`."""
    return unpack_image(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
