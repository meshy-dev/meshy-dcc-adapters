"""Save an image datablock back to disk."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._image_light_ops import save_image


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`save_image`."""
    return save_image(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
