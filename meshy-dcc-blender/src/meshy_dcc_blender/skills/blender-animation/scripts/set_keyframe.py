"""Insert a keyframe on a Blender object."""

from __future__ import annotations

from typing import List, Optional

from meshy_dcc_core.skill import skill_entry, skill_error, skill_exception, skill_success

from meshy_dcc_blender._animation_ops import action_fcurves
from meshy_dcc_blender._modeling_common import rotation_data_path

DEFAULT_DATA_PATHS = ["location", "rotation_euler", "scale"]


def set_keyframe(
    object_name: str,
    frame: Optional[int] = None,
    data_paths: Optional[List[str]] = None,
    interpolation: Optional[str] = None,
) -> dict:
    """Insert keyframes on an object.

    Args:
        object_name: Name of the object to keyframe.
        frame: Frame number. If None, uses the current scene frame.
        data_paths: List of data paths to keyframe, e.g. ["location", "rotation_euler", "scale"].
            Defaults to all three transform channels.

    Returns:
        ActionResultModel dict.
    """
    try:
        import bpy

        obj = bpy.data.objects.get(object_name)
        if obj is None:
            return skill_error(f"Object not found: {object_name}", f"No object named '{object_name}'.")

        scene = bpy.context.scene
        # Key first, then move the playhead: frame_set re-evaluates existing
        # curves and would overwrite the values the caller just set.
        actual_frame = frame if frame is not None else scene.frame_current

        mode = interpolation.upper() if interpolation else None
        if mode not in {None, "BEZIER", "LINEAR", "CONSTANT"}:
            return skill_error("Unsupported interpolation", "Use BEZIER, LINEAR, or CONSTANT.")
        preferences = getattr(getattr(bpy.context, "preferences", None), "edit", None)
        previous_mode = getattr(preferences, "keyframe_new_interpolation_type", None)
        # rotation_euler stands for whichever rotation property the object uses.
        rotation = rotation_data_path(obj)
        paths = [rotation if path == "rotation_euler" else path for path in data_paths or DEFAULT_DATA_PATHS]
        inserted = []
        try:
            if mode is not None and preferences is not None:
                preferences.keyframe_new_interpolation_type = mode
            for path in paths:
                obj.keyframe_insert(data_path=path, frame=actual_frame)
                if mode is not None:
                    for _, fcurve in action_fcurves(obj):
                        if getattr(fcurve, "data_path", None) != path:
                            continue
                        for key in getattr(fcurve, "keyframe_points", []):
                            co = getattr(key, "co", ())
                            key_frame = float(co.x if hasattr(co, "x") else co[0])
                            if abs(key_frame - actual_frame) < 1e-4:
                                key.interpolation = mode
                inserted.append(path)
        finally:
            if previous_mode is not None:
                preferences.keyframe_new_interpolation_type = previous_mode
        if frame is not None:
            scene.frame_set(frame)

        return skill_success(
            f"Keyframe set on {object_name} at frame {actual_frame}",
            object_name=object_name,
            frame=actual_frame,
            data_paths=inserted,
            interpolation=mode,
            prompt="Keyframe inserted. Use set_current_frame to navigate the timeline.",
        )
    except ImportError:
        return skill_error("Blender not available", "bpy could not be imported")
    except Exception as exc:
        return skill_exception(exc, message=f"Failed to set keyframe on {object_name}")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_keyframe`."""
    return set_keyframe(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
