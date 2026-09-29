"""Render the open level around an actor into a PNG.

An explicit scene capture renders on request, so this works while the
editor is in the background and its viewports stop drawing (a capture set to
render every frame would stay black then), and it leaves the viewport camera
where the user put it. Nanite geometry and textures stream in per view, so
the capture renders once per editor tick for a while before the PNG is
written; this tool runs off the editor thread and hands each step to it.
"""

from __future__ import annotations

import math
import os
import re
import time

from _meshy import editor_world, find_actor, on_editor, project_dir
from meshy_dcc_core.skill import skill_entry, skill_error, skill_success

# Where the camera sits relative to the actor. An imported Meshy model faces +Y (Unreal is Z up and
# left-handed), so its left side is +X.
VIEWS = {
    "front": (0.0, 1.0, 0.25),
    "back": (0.0, -1.0, 0.25),
    "left": (1.0, 0.0, 0.25),
    "right": (-1.0, 0.0, 0.25),
    "top": (0.0, 0.0, 1.0),
    "three_quarter": (0.6, 0.8, 0.45),
}
FIELD_OF_VIEW = 40.0  # horizontal, as Unreal measures it
# Renders before the PNG is written, so streaming catches up with the new view.
WARM_UP_FRAMES = 30
WARM_UP_SECONDS = 2.0


def camera_for(unreal, found, view: str, width: int, height: int):
    origin, extent = found.get_actor_bounds(False)
    radius = max(float(extent.length()), 1.0)
    horizontal = math.radians(FIELD_OF_VIEW)
    vertical = 2 * math.atan(math.tan(horizontal / 2) * height / width)
    distance = radius / math.tan(min(horizontal, vertical) / 2) * 1.05
    x, y, z = VIEWS[view]
    length = math.sqrt(x * x + y * y + z * z)
    camera = unreal.Vector(
        origin.x + x / length * distance, origin.y + y / length * distance, origin.z + z / length * distance
    )
    return camera, unreal.MathLibrary.find_look_at_rotation(camera, origin)


def _start(unreal, actor: str, view: str, width: int, height: int):
    """On the editor thread: place a temporary scene capture."""
    found = None
    if actor:
        found = find_actor(unreal, actor)
        if found is None:
            return None
        camera, rotation = camera_for(unreal, found, view, width, height)
    else:
        camera, rotation = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
    world = editor_world(unreal)
    target = unreal.RenderingLibrary.create_render_target2d(world, width, height, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    capture = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        unreal.SceneCapture2D, camera, rotation, transient=True
    )
    component = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    component.set_editor_property("texture_target", target)
    component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    component.set_editor_property("fov_angle", FIELD_OF_VIEW)
    component.set_editor_property("capture_every_frame", False)
    if found is not None:
        mesh = found.get_component_by_class(unreal.StaticMeshComponent)
        for index in range(mesh.get_num_materials() if mesh else 0):
            material = mesh.get_material(index)
            for texture in unreal.MaterialEditingLibrary.get_used_textures(material) if material else []:
                if isinstance(texture, unreal.Texture2D):
                    texture.set_force_mip_levels_to_be_resident(30.0, 0)
    return world, target, capture, component


def _finish(unreal, world, target, capture, component, directory: str, name: str) -> bool:
    """On the editor thread: write the PNG unless nothing rendered, then remove the scene capture."""
    try:
        width, height = target.get_editor_property("size_x"), target.get_editor_property("size_y")
        samples = [
            unreal.RenderingLibrary.read_render_target_pixel(world, target, width * i // 6, height * j // 6)
            for i in range(1, 6)
            for j in range(1, 6)
        ]
        if not any(color.r or color.g or color.b for color in samples):
            return False
        unreal.RenderingLibrary.export_render_target(world, target, directory, name)
        return True
    finally:
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(capture)


@skill_entry
def capture_model(actor: str = "", view: str = "front", file_name: str = "", width: int = 1280, height: int = 720,
                  **kwargs) -> dict:
    import unreal  # noqa: PLC0415

    if view not in VIEWS:
        return skill_error(f"Unknown view {view!r}", f"Use one of {', '.join(VIEWS)}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", file_name or "capture"):
        return skill_error("file_name may hold only letters, digits, _ and -", f"Got {file_name!r}")
    started = on_editor(_start, unreal, actor, view, int(width), int(height))
    if started is None:
        return skill_error(f"No actor labelled {actor!r} in the open level", "List actors with unreal-actors")
    directory = on_editor(lambda: os.path.join(project_dir(unreal), "Saved", "MeshyDcc"))
    os.makedirs(directory, exist_ok=True)
    name = f"{file_name or 'capture'}.png"
    component = started[3]
    deadline = time.monotonic() + WARM_UP_SECONDS
    rendered = False
    try:
        renders = 0
        while renders < WARM_UP_FRAMES or time.monotonic() < deadline:
            on_editor(component.capture_scene)  # one render per editor tick
            renders += 1
    finally:
        rendered = on_editor(_finish, unreal, *started, directory, name)
    path = os.path.join(directory, name)
    if not rendered:
        return skill_error("The capture rendered nothing", "Every sampled pixel is black; check the Output Log")
    if not os.path.isfile(path):
        return skill_error("The capture was not written", f"No file at {path}; check the Output Log")
    return skill_success("Captured the level", path=path, view=view if actor else "viewport_camera")
