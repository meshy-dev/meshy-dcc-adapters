"""Rotate an object by Euler angles (degrees)."""

from __future__ import annotations

from typing import List

from meshy_dcc_core.skill import skill_entry, skill_error, skill_exception, skill_success

from meshy_dcc_blender._modeling_common import set_rotation_degrees


def rotate_object(name: str, rotation: List[float]) -> dict:
    """Set an object's rotation from Euler angles, through the property its rotation_mode uses.

    Args:
        name: Name of the object to rotate.
        rotation: [rx, ry, rz] rotation in **degrees**.

    Returns:
        ActionResultModel dict.
    """
    try:
        import bpy

        obj = bpy.data.objects.get(name)
        if obj is None:
            return skill_error(f"Object not found: {name}", f"No object named '{name}' in the scene.")

        actual_deg = set_rotation_degrees(obj, rotation)
        return skill_success(
            f"Rotated {name}",
            object_name=name,
            rotation_degrees=actual_deg,
            rotation_mode=getattr(obj, "rotation_mode", None),
            prompt="Object rotated. Use get_object_info to verify the new rotation.",
        )
    except ImportError:
        return skill_error("Blender not available", "bpy could not be imported")
    except Exception as exc:
        return skill_exception(exc, message=f"Failed to rotate object: {name}")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rotate_object`."""
    # ``object_name``, as the other object tools call it, is accepted for ``name``.
    if "object_name" in kwargs:
        kwargs["name"] = kwargs.pop("object_name")
    if not kwargs.get("name"):
        return skill_error("Object name is required", "Pass object_name (or its alias name).")
    return rotate_object(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
