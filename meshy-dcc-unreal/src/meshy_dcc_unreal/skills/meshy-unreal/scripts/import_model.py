"""Import a Meshy GLB or FBX into /Game/Meshy/<name> and place it in the open level."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from _meshy import MODEL_EXTENSIONS, MODEL_ROOT, actor_info, asset_name, level_path, mesh_info, unsaved_packages
from meshy_dcc_core.skill import skill_entry, skill_error, skill_success

TEXTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tga")
# A Meshy "FBX with textures" download: <stem>.fbx next to <stem>.png and <stem>_<map>.png.
MESHY_SUFFIXES = {"base_color": "", "normal": "_normal", "metallic": "_metallic", "roughness": "_roughness"}


def meshy_texture_set(source_path: str) -> Dict[str, str]:
    stem = os.path.splitext(source_path)[0]
    return {key: f"{stem}{suffix}.png" for key, suffix in MESHY_SUFFIXES.items() if os.path.isfile(f"{stem}{suffix}.png")}


def _import(unreal: Any, filename: str, folder: str, name: str) -> List[str]:
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filename)
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return [str(path) for path in task.get_editor_property("imported_object_paths")]


def build_pbr_material(unreal: Any, folder: str, name: str, files: Dict[str, str]) -> Any:
    """One Material wired from the texture set: sRGB base colour, normal map, linear metallic and roughness."""
    layout = {
        "base_color": ("MP_BASE_COLOR", "RGB", "SAMPLERTYPE_COLOR", True, "TC_DEFAULT"),
        "normal": ("MP_NORMAL", "RGB", "SAMPLERTYPE_NORMAL", False, "TC_NORMALMAP"),
        "metallic": ("MP_METALLIC", "R", "SAMPLERTYPE_MASKS", False, "TC_MASKS"),
        "roughness": ("MP_ROUGHNESS", "R", "SAMPLERTYPE_MASKS", False, "TC_MASKS"),
    }
    library = unreal.MaterialEditingLibrary
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        f"M_{name}", folder, unreal.Material, unreal.MaterialFactoryNew()
    )
    for row, (key, path) in enumerate(sorted(files.items())):
        prop, output, sampler, srgb, compression = layout[key]
        texture = next(
            (asset for asset in map(unreal.EditorAssetLibrary.load_asset, _import(unreal, path, folder, f"T_{name}_{key}"))
             if isinstance(asset, unreal.Texture2D)),
            None,
        )
        if texture is None:
            raise RuntimeError(f"{os.path.basename(path)} did not import as a texture")
        texture.set_editor_property("srgb", srgb)
        texture.set_editor_property("compression_settings", getattr(unreal.TextureCompressionSettings, compression))
        if key == "normal":
            # Meshy normal maps are OpenGL style (green up); Unreal expects green down.
            texture.set_editor_property("flip_green_channel", True)
        node = library.create_material_expression(material, unreal.MaterialExpressionTextureSample, -420, row * 280)
        node.set_editor_property("texture", texture)
        node.set_editor_property("sampler_type", getattr(unreal.MaterialSamplerType, sampler))
        library.connect_material_property(node, output, getattr(unreal.MaterialProperty, prop))
    library.recompile_material(material)
    return material


@skill_entry
def import_model(
    source_path: str = "",
    name: str = "",
    textures: Optional[Dict[str, str]] = None,
    place: bool = True,
    location: Optional[List[float]] = None,
    **kwargs,
) -> dict:
    import unreal  # noqa: PLC0415

    if not os.path.isabs(source_path) or not os.path.isfile(source_path):
        return skill_error("source_path must be an existing absolute file", f"Not a file: {source_path!r}")
    extension = os.path.splitext(source_path)[1].lower()
    if extension not in MODEL_EXTENSIONS:
        return skill_error(f"Unsupported model format {extension!r}", "Import a .glb, .gltf or .fbx file")
    texture_files = dict(textures or {})
    unknown = sorted(set(texture_files) - set(MESHY_SUFFIXES))
    if unknown:
        return skill_error(f"Unknown texture roles {unknown}", f"Use {', '.join(MESHY_SUFFIXES)}")
    for role, path in texture_files.items():
        if not os.path.isabs(path) or not os.path.isfile(path) or not path.lower().endswith(TEXTURE_EXTENSIONS):
            return skill_error(f"textures.{role} must be an existing absolute image", f"Not usable: {path!r}")
    if not texture_files and extension == ".fbx":
        texture_files = meshy_texture_set(source_path)
    name = asset_name(name or os.path.splitext(os.path.basename(source_path))[0])
    folder = f"{MODEL_ROOT}/{name}"
    assets = unreal.EditorAssetLibrary
    if assets.does_directory_exist(folder) and assets.list_assets(folder, recursive=True):
        return skill_error(f"{folder} already holds assets", "Pass another name; this tool never replaces assets")
    level = level_path(unreal)
    if place and not (level and level.startswith("/Game/")):
        return skill_error(
            f"The open level {level} is not part of the project",
            "Create or load a level under /Game with unreal-level first, or pass place: false",
        )

    _import(unreal, source_path, folder, name if extension == ".fbx" else "")
    meshes = [
        mesh
        for mesh in (assets.load_asset(path) for path in assets.list_assets(folder, recursive=True))
        if isinstance(mesh, unreal.StaticMesh)
    ]
    if not meshes:
        return skill_error(
            f"Importing {os.path.basename(source_path)} produced no static mesh",
            "Check the Output Log for importer errors",
            imported_assets=sorted(str(path) for path in assets.list_assets(folder, recursive=True)),
        )
    pbr = None
    if texture_files:
        # The FBX importer's own material treats roughness as shininess; replace it on every slot.
        material = build_pbr_material(unreal, folder, name, texture_files)
        for mesh in meshes:
            for index in range(len(mesh.get_editor_property("static_materials"))):
                mesh.set_material(index, material)
        pbr = {"material": material.get_path_name(), "textures": texture_files}
    assets.save_directory(folder, only_if_is_dirty=True, recursive=True)

    result: Dict[str, Any] = {
        "folder": folder,
        "imported_assets": sorted(str(path) for path in assets.list_assets(folder, recursive=True)),
        "pbr": pbr,
        "meshes": [mesh_info(unreal, mesh) for mesh in meshes],
    }
    if place:
        # location is where the base of the model goes; Meshy models are centred on their origin.
        bounds = meshes[0].get_bounds()
        x, y, z = location or [0.0, 0.0, 0.0]
        position = unreal.Vector(
            x - float(bounds.origin.x),
            y - float(bounds.origin.y),
            z + float(bounds.box_extent.z) - float(bounds.origin.z),
        )
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        with unreal.ScopedEditorTransaction(f"Meshy: place {name}"):
            actor = actors.spawn_actor_from_object(meshes[0], position)
            actor.set_actor_label(name)
        result["actor"] = actor_info(unreal, actor)
    return skill_success(
        f"Imported {name} into {folder}" + (" and placed it in the level" if place else ""),
        prompt="The assets are saved; the level is not. Save it with unreal-level save_level when asked.",
        unsaved=unsaved_packages(unreal),
        **result,
    )
