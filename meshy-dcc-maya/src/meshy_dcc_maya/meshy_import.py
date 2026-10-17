"""Meshy model handoff for Maya: import an FBX or OBJ with a PBR standardSurface, and read it back.

The ``meshy-maya`` skill's tools call these functions on Maya's main thread.

A Meshy "FBX with textures" download is ``<stem>.fbx`` next to
``<stem>.png`` and ``<stem>_<map>.png``. FBX cannot carry metallic or
roughness maps, so the import rebuilds one ``standardSurface`` (Maya's own PBR
shader, no Arnold needed) from that texture set and assigns it to every
imported mesh:

======================  =======================  ============  ============
role                    standardSurface input    colour space  file output
======================  =======================  ============  ============
base_color              baseColor                sRGB          outColor
metallic                metalness                Raw           outColorR
roughness               specularRoughness        Raw           outColorR
metallic_roughness      metalness / roughness    Raw           outColorB / outColorG
emission                emissionColor            sRGB          outColor
normal                  normalCamera (bump2d,    Raw           outAlpha
                        tangent-space normals)
======================  =======================  ============  ============

A packed ``metallic_roughness`` map follows glTF: green is roughness, blue is
metalness. Each file node ignores the colour-space file rules, so a rule
cannot turn a data map back into sRGB.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from meshy_dcc_core.skill import skill_error, skill_success

MODEL_TYPES = {".fbx": ("fbxmaya", "FBX"), ".obj": ("objExport", "OBJ")}
TEXTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".exr")
MESHY_SUFFIXES = {
    "base_color": "",
    "normal": "_normal",
    "metallic": "_metallic",
    "roughness": "_roughness",
    "metallic_roughness": "_metallic_roughness",
    "emission": "_emission",
}
COLOR_ROLES = ("base_color", "emission")
PBR_INPUTS = ("baseColor", "metalness", "specularRoughness", "emissionColor", "normalCamera")
_PLACE2D_LINKS = (
    "coverage",
    "translateFrame",
    "rotateFrame",
    "mirrorU",
    "mirrorV",
    "stagger",
    "wrapU",
    "wrapV",
    "repeatUV",
    "offset",
    "rotateUV",
    "noiseUV",
    "vertexUvOne",
    "vertexUvTwo",
    "vertexUvThree",
    "vertexCameraOne",
)


def node_name(raw: str) -> str:
    """A Maya node name: letters, digits and underscores, starting with a letter."""
    name = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")[:64]
    return name if name[:1].isalpha() else "Meshy_{}".format(name).rstrip("_")


def meshy_texture_set(source_path: str) -> Dict[str, str]:
    """The Meshy maps next to ``source_path``: ``<stem>.png``, ``<stem>_normal.png`` and so on."""
    stem = os.path.splitext(source_path)[0]
    found = {}
    for role, suffix in MESHY_SUFFIXES.items():
        for extension in (".png", ".jpg", ".jpeg"):
            candidate = stem + suffix + extension
            if os.path.isfile(candidate):
                found[role] = candidate
                break
    return found


def _file_node(cmds: Any, name: str, path: str, color_space: str) -> str:
    node = cmds.shadingNode("file", asTexture=True, isColorManaged=True, name=name)
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=name + "_place2d")
    for attr in _PLACE2D_LINKS:
        cmds.connectAttr("{}.{}".format(place, attr), "{}.{}".format(node, attr), force=True)
    cmds.connectAttr(place + ".outUV", node + ".uvCoord", force=True)
    cmds.connectAttr(place + ".outUvFilterSize", node + ".uvFilterSize", force=True)
    cmds.setAttr(node + ".fileTextureName", path.replace("\\", "/"), type="string")
    cmds.setAttr(node + ".colorSpace", color_space, type="string")
    cmds.setAttr(node + ".ignoreColorSpaceFileRules", True)
    return node


def build_standard_surface(cmds: Any, name: str, textures: Dict[str, str]) -> Dict[str, str]:
    """One standardSurface wired from ``textures``; returns the shader and shading group names."""
    shader = cmds.shadingNode("standardSurface", asShader=True, name=name + "_mat")
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "_matSG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader", force=True)
    # glTF base colour is the full albedo; standardSurface scales it by base (0.8 by default).
    cmds.setAttr(shader + ".base", 1.0)

    def wire(role: str, output: str, target: str) -> None:
        color_space = "sRGB" if role in COLOR_ROLES else "Raw"
        node = _file_node(cmds, "{}_{}".format(name, role), textures[role], color_space)
        cmds.connectAttr("{}.{}".format(node, output), "{}.{}".format(shader, target), force=True)

    if "base_color" in textures:
        wire("base_color", "outColor", "baseColor")
    packed = "metallic_roughness" in textures
    if "metallic" in textures:
        wire("metallic", "outColorR", "metalness")
    if "roughness" in textures:
        wire("roughness", "outColorR", "specularRoughness")
    if packed and not ("metallic" in textures and "roughness" in textures):
        node = _file_node(cmds, name + "_metallic_roughness", textures["metallic_roughness"], "Raw")
        if "metallic" not in textures:
            cmds.connectAttr(node + ".outColorB", shader + ".metalness", force=True)
        if "roughness" not in textures:
            cmds.connectAttr(node + ".outColorG", shader + ".specularRoughness", force=True)
    if "emission" in textures:
        cmds.setAttr(shader + ".emission", 1.0)
        wire("emission", "outColor", "emissionColor")
    if "normal" in textures:
        node = _file_node(cmds, name + "_normal", textures["normal"], "Raw")
        bump = cmds.shadingNode("bump2d", asUtility=True, name=name + "_normal_bump2d")
        cmds.setAttr(bump + ".bumpInterp", 1)  # tangent-space normals
        cmds.connectAttr(node + ".outAlpha", bump + ".bumpValue", force=True)
        cmds.connectAttr(bump + ".outNormal", shader + ".normalCamera", force=True)
    return {"shader": shader, "shading_group": group}


def _meshes(cmds: Any, root: str) -> List[str]:
    shapes = cmds.listRelatives(root, allDescendents=True, type="mesh", fullPath=True) or []
    return [shape for shape in shapes if not cmds.getAttr(shape + ".intermediateObject")]


def _source(cmds: Any, plug: str) -> Optional[str]:
    sources = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
    return sources[0] if sources else None


def _texture(cmds: Any, file_node: str, output: str) -> Dict[str, Any]:
    path = cmds.getAttr(file_node + ".fileTextureName") or ""
    return {
        "file_node": file_node,
        "output": output,
        "path": path,
        "exists": bool(path) and os.path.isfile(path),
        "color_space": cmds.getAttr(file_node + ".colorSpace"),
        "ignore_color_space_file_rules": bool(cmds.getAttr(file_node + ".ignoreColorSpaceFileRules")),
    }


def shader_info(cmds: Any, shader: str) -> Dict[str, Any]:
    """The shader type and, per PBR input, the texture feeding it, its colour space and channel."""
    info: Dict[str, Any] = {"shader": shader, "type": cmds.nodeType(shader), "inputs": {}}
    if info["type"] != "standardSurface":
        return info
    info["base"] = cmds.getAttr(shader + ".base")
    info["emission"] = cmds.getAttr(shader + ".emission")
    for attr in PBR_INPUTS:
        plug = _source(cmds, "{}.{}".format(shader, attr))
        if plug is None:
            continue
        node, output = plug.split(".", 1)
        kind = cmds.nodeType(node)
        if kind == "file":
            info["inputs"][attr] = _texture(cmds, node, output)
        elif kind == "bump2d":
            entry: Dict[str, Any] = {"bump2d": node, "use_as": cmds.getAttr(node + ".bumpInterp")}
            value = _source(cmds, node + ".bumpValue")
            if value is not None and cmds.nodeType(value.split(".", 1)[0]) == "file":
                entry.update(_texture(cmds, *value.split(".", 1)))
            info["inputs"][attr] = entry
        else:
            info["inputs"][attr] = {"node": node, "type": kind, "output": output}
    return info


def model_info(cmds: Any, root: str) -> Dict[str, Any]:
    """Meshes, counts, world bounds and materials under ``root``."""
    meshes = []
    shaders: Dict[str, Dict[str, Any]] = {}
    for shape in _meshes(cmds, root):
        groups = sorted(set(cmds.listConnections(shape, type="shadingEngine") or []))
        materials = []
        for group in groups:
            for shader in cmds.listConnections(group + ".surfaceShader", source=True, destination=False) or []:
                materials.append(shader)
                if shader not in shaders:
                    shaders[shader] = shader_info(cmds, shader)
        meshes.append(
            {
                "shape": shape,
                "vertices": cmds.polyEvaluate(shape, vertex=True),
                "faces": cmds.polyEvaluate(shape, face=True),
                "triangles": cmds.polyEvaluate(shape, triangle=True),
                "shading_groups": groups,
                "materials": materials,
            }
        )
    bounds = [round(float(value), 4) for value in cmds.exactWorldBoundingBox(root)]
    return {
        "node": root,
        "meshes": meshes,
        "bounds": {"min": bounds[:3], "max": bounds[3:], "size": [round(bounds[i + 3] - bounds[i], 4) for i in range(3)]},
        "linear_unit": cmds.currentUnit(query=True, linear=True),
        "up_axis": cmds.upAxis(query=True, axis=True),
        "materials": list(shaders.values()),
    }


def _scene(cmds: Any) -> Dict[str, Any]:
    return {
        "scene_file": cmds.file(query=True, sceneName=True) or None,
        "scene_modified": bool(cmds.file(query=True, modified=True)),
    }


def import_model(cmds: Any, source_path: str = "", name: str = "", textures: Optional[Dict[str, str]] = None) -> dict:
    """Import one Meshy FBX or OBJ under a new group ``name``, rebuild its PBR material, read it back."""
    if not os.path.isabs(source_path) or not os.path.isfile(source_path):
        return skill_error("source_path must be an existing absolute file", "Not a file: {!r}".format(source_path))
    extension = os.path.splitext(source_path)[1].lower()
    if extension not in MODEL_TYPES:
        return skill_error(
            "Unsupported model format {!r}".format(extension),
            "Import a .fbx or .obj file; Maya has no built-in glTF importer, so download Meshy's FBX",
        )
    texture_files = dict(textures or {})
    unknown = sorted(set(texture_files) - set(MESHY_SUFFIXES))
    if unknown:
        return skill_error("Unknown texture roles {}".format(unknown), "Use {}".format(", ".join(MESHY_SUFFIXES)))
    for role, path in texture_files.items():
        if not os.path.isabs(path) or not os.path.isfile(path) or not path.lower().endswith(TEXTURE_EXTENSIONS):
            return skill_error("textures.{} must be an existing absolute image".format(role), "Not usable: {!r}".format(path))
    if not texture_files:
        texture_files = meshy_texture_set(source_path)
    name = node_name(name or os.path.splitext(os.path.basename(source_path))[0])
    taken = [node for node in (name, name + "_mat", name + "_matSG") if cmds.objExists(node)]
    if taken:
        return skill_error(
            "{} already exists in the scene".format(", ".join(taken)),
            "Pass another name; this tool never replaces nodes",
        )

    plugin, file_type = MODEL_TYPES[extension]
    if not cmds.pluginInfo(plugin, query=True, loaded=True):
        cmds.loadPlugin(plugin, quiet=True)
    cmds.undoInfo(openChunk=True, chunkName="Meshy import " + name)
    try:
        before = set(cmds.ls(assemblies=True, long=True) or [])
        cmds.file(source_path, i=True, type=file_type, ignoreVersion=True, mergeNamespacesOnClash=False, prompt=False)
        tops = [node for node in cmds.ls(assemblies=True, long=True) or [] if node not in before]
        if not tops:
            return skill_error(
                "Importing {} added nothing to the scene".format(os.path.basename(source_path)),
                "Check the Script Editor for importer errors",
            )
        group = cmds.group(tops, name=name, world=True)
        meshes = _meshes(cmds, group)
        if not meshes:
            return skill_error(
                "Importing {} produced no mesh".format(os.path.basename(source_path)),
                "Check the Script Editor for importer errors",
                group=group,
            )
        material = None
        if texture_files:
            material = build_standard_surface(cmds, name, texture_files)
            cmds.sets(meshes, edit=True, forceElement=material["shading_group"])
            material["textures"] = texture_files
    finally:
        cmds.undoInfo(closeChunk=True)
    return skill_success(
        "Imported {} as {}".format(os.path.basename(source_path), group)
        + (" with a standardSurface from {} map(s)".format(len(texture_files)) if material else ""),
        prompt="The scene is not saved. Read it back with inspect_model; save with maya-scene save_scene when asked.",
        group=group,
        pbr=material,
        model=model_info(cmds, group),
        **_scene(cmds),
    )


def inspect_model(cmds: Any, node: str = "") -> dict:
    """Read back a group or mesh transform: meshes, counts, bounds, materials and their textures."""
    if not node or not cmds.objExists(node):
        return skill_error("No node {!r} in the scene".format(node), "Pass the group name import_model returned")
    return skill_success("Read back {}".format(node), model=model_info(cmds, node), **_scene(cmds))
