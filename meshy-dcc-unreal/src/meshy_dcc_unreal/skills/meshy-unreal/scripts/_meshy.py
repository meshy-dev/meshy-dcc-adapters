"""Shared readback for the meshy-unreal tools. Runs inside the Unreal Editor."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from meshy_dcc_unreal._safe_stop import dirty_packages, unsaved_packages  # noqa: F401 - re-exported

MODEL_ROOT = "/Game/Meshy"
MODEL_EXTENSIONS = (".glb", ".gltf", ".fbx")
MATERIAL_OUTPUTS = (
    ("base_color", "MP_BASE_COLOR"),
    ("normal", "MP_NORMAL"),
    ("metallic", "MP_METALLIC"),
    ("roughness", "MP_ROUGHNESS"),
    ("emissive", "MP_EMISSIVE_COLOR"),
)


def asset_name(raw: str) -> str:
    """A Content Browser safe name: letters, digits and underscores, starting with a letter."""
    name = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")[:64]
    return name if name[:1].isalpha() else f"M_{name}".rstrip("_")


def on_editor(func: Any, *args: Any) -> Any:
    """Run ``func`` on the editor thread; from another thread this returns after the next editor tick."""
    from meshy_dcc_unreal import server  # noqa: PLC0415

    instance = server._server_instance
    if instance is None:
        return func(*args)
    return instance._main_thread_dispatcher.dispatch_callable(func, *args, affinity="main", timeout_hint_secs=60)


def vec(value: Any) -> List[float]:
    return [round(float(value.x), 4), round(float(value.y), 4), round(float(value.z), 4)]


def project_dir(unreal: Any) -> str:
    return os.path.realpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))


def editor_world(unreal: Any) -> Any:
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def level_path(unreal: Any) -> Optional[str]:
    world = editor_world(unreal)
    return str(world.get_outermost().get_name()) if world is not None else None


def _try(call: Any, *args: Any) -> Any:
    try:
        return call(*args)
    except Exception:  # noqa: BLE001 - readback reports what the engine exposes
        return None


def texture_info(unreal: Any, texture: Any) -> Dict[str, Any]:
    info: Dict[str, Any] = {"texture": texture.get_path_name()}
    srgb = _try(texture.get_editor_property, "srgb")
    if srgb is not None:
        info["srgb"] = bool(srgb)
    compression = _try(texture.get_editor_property, "compression_settings")
    if compression is not None:
        info["compression"] = str(getattr(compression, "name", compression))
    flip = _try(texture.get_editor_property, "flip_green_channel")
    if flip is not None:
        info["flip_green_channel"] = bool(flip)
    return info


def _ours(path: str) -> bool:
    """Project assets, not the engine's placeholder textures and defaults."""
    return path.startswith(("/Game/", "/Temp/"))


def material_info(unreal: Any, material: Any, slot: Optional[str] = None) -> Dict[str, Any]:
    info: Dict[str, Any] = {"slot": slot, "material": material.get_path_name() if material else None}
    if material is None:
        return info
    info["class"] = material.get_class().get_name()
    library = unreal.MaterialEditingLibrary
    textures: Dict[str, Any] = {}
    if isinstance(material, unreal.MaterialInstance):
        parent = _try(material.get_editor_property, "parent")
        info["parent"] = parent.get_path_name() if parent else None
        for name in _try(library.get_texture_parameter_names, material) or []:
            texture = _try(library.get_material_instance_texture_parameter_value, material, name)
            if texture is not None and _ours(texture.get_path_name()):
                textures[str(name)] = texture_info(unreal, texture)
        scalars: Dict[str, float] = {}
        for name in _try(library.get_scalar_parameter_names, material) or []:
            if str(name).endswith(("_Rotation", "_TexCoord")) or str(name).startswith(("Iridescence", "Anisotropy")):
                continue
            value = _try(library.get_material_instance_scalar_parameter_value, material, name)
            if value is not None:
                scalars[str(name)] = round(float(value), 4)
        info["scalar_parameters"] = scalars
        vectors: Dict[str, List[float]] = {}
        for name in _try(library.get_vector_parameter_names, material) or []:
            if str(name).endswith(("_OffsetScale", "_TilingMethod")) or str(name).startswith(("Iridescence", "Anisotropy")):
                continue
            value = _try(library.get_material_instance_vector_parameter_value, material, name)
            if value is not None:
                vectors[str(name)] = [round(float(value.r), 4), round(float(value.g), 4),
                                      round(float(value.b), 4), round(float(value.a), 4)]
        info["vector_parameters"] = vectors
    else:
        # Which texture feeds which output shows the wiring, not just which textures are used.
        for role, output in MATERIAL_OUTPUTS:
            node = _try(library.get_material_property_input_node, material, getattr(unreal.MaterialProperty, output))
            texture = _try(node.get_editor_property, "texture") if isinstance(node, unreal.MaterialExpressionTextureBase) else None
            if texture is not None:
                textures[role] = texture_info(unreal, texture)
        for texture in _try(library.get_used_textures, material) or []:
            if texture is not None and _ours(texture.get_path_name()) and all(
                entry["texture"] != texture.get_path_name() for entry in textures.values()
            ):
                textures[texture.get_name()] = texture_info(unreal, texture)
    info["textures"] = textures
    return info


def mesh_info(unreal: Any, mesh: Any) -> Dict[str, Any]:
    info: Dict[str, Any] = {"asset": mesh.get_path_name(), "class": mesh.get_class().get_name()}
    if isinstance(mesh, unreal.StaticMesh):
        info["lods"] = _try(mesh.get_num_lods)
        info["vertices"] = _try(mesh.get_num_vertices, 0)
        info["triangles"] = _try(mesh.get_num_triangles, 0)
        info["sections"] = _try(mesh.get_num_sections, 0)
        nanite = _try(mesh.get_editor_property, "nanite_settings")
        # With Nanite on, the counts above come from the fallback mesh once the editor has reloaded it.
        info["nanite"] = None if nanite is None else bool(nanite.get_editor_property("enabled"))
        bounds = _try(mesh.get_bounds)
        if bounds is not None:
            info["bounds"] = {"origin": vec(bounds.origin), "extent": vec(bounds.box_extent)}
        slots = _try(mesh.get_editor_property, "static_materials") or []
        info["materials"] = [
            material_info(unreal, slot.get_editor_property("material_interface"), str(slot.material_slot_name))
            for slot in slots
        ]
    return info


def find_actor(unreal: Any, label: str) -> Optional[Any]:
    """The level actor whose label, or else object name, is ``label``."""
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for key in ("get_actor_label", "get_name"):
        for actor in actors:
            if str(getattr(actor, key)()) == label:
                return actor
    return None


def actor_info(unreal: Any, actor: Any) -> Dict[str, Any]:
    rotation = actor.get_actor_rotation()
    info: Dict[str, Any] = {
        "actor": actor.get_name(),
        "label": actor.get_actor_label(),
        "level": level_path(unreal),
        "location": vec(actor.get_actor_location()),
        "rotation": {
            "roll": round(float(rotation.roll), 4),
            "pitch": round(float(rotation.pitch), 4),
            "yaw": round(float(rotation.yaw), 4),
        },
        "scale": vec(actor.get_actor_scale3d()),
    }
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component is not None:
        mesh = component.get_editor_property("static_mesh")
        info["mesh"] = mesh_info(unreal, mesh) if mesh is not None else None
        info["component_materials"] = [
            (material.get_path_name() if material else None)
            for material in (component.get_material(index) for index in range(component.get_num_materials()))
        ]
    return info
