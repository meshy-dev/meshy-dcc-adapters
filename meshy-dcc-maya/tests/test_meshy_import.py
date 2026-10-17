"""meshy-maya import and readback against a small stand-in for maya.cmds."""

import os

import pytest

from meshy_dcc_maya import meshy_import


class FakeCmds:
    """Just enough of maya.cmds: nodes, attributes, connections, one FBX import."""

    def __init__(self, imported=("|Body",)):
        self.types = {"|persp": "transform"}
        self.attrs = {}
        self.links = []  # (source plug, destination plug)
        self.parents = {}
        self.members = {}
        self.plugins = set()
        self.chunks = []
        self.imported = imported
        self.modified = False

    # nodes
    def objExists(self, name):
        return name in self.types or name.lstrip("|") in {n.lstrip("|") for n in self.types}

    def nodeType(self, name):
        return self.types[name]

    def shadingNode(self, kind, name, **_):
        while name in self.types:
            name += "1"
        self.types[name] = kind
        return name

    def sets(self, members=None, edit=False, forceElement=None, name=None, **_):
        if edit:
            self.members.setdefault(forceElement, []).extend(members)
            for shape in members:
                self.links.append((forceElement + ".message", shape + ".instObjGroups"))
            return None
        self.types[name] = "shadingEngine"
        return name

    def group(self, nodes, name, world):
        self.types[name] = "transform"
        for node in nodes:
            self.parents[node] = name
        return name

    def ls(self, assemblies=False, long=False):
        return [n for n, t in self.types.items() if t == "transform" and n.startswith("|") and n not in self.parents]

    def listRelatives(self, root, allDescendents, type, fullPath):
        return [n for n, t in self.types.items() if t == "mesh" and self.parents.get(self.parents.get(n)) == root]

    # attributes and connections
    def setAttr(self, plug, value, type=None):
        self.attrs[plug] = value

    def getAttr(self, plug):
        return self.attrs.get(plug, 0)

    def connectAttr(self, source, destination, force):
        self.links.append((source, destination))

    def listConnections(self, plug, type=None, source=True, destination=True, plugs=False):
        if type == "shadingEngine":
            return [s.split(".")[0] for s, d in self.links if d.split(".")[0] == plug and self.types.get(s.split(".")[0]) == type]
        found = [s for s, d in self.links if d == plug]
        return found if plugs else [s.split(".")[0] for s in found]

    # scene
    def pluginInfo(self, name, query, loaded):
        return name in self.plugins

    def loadPlugin(self, name, quiet):
        self.plugins.add(name)

    def undoInfo(self, **kwargs):
        self.chunks.append(kwargs)

    def file(self, path=None, i=False, query=False, sceneName=False, modified=False, **_):
        if query:
            return "" if sceneName else self.modified
        for top in self.imported:
            self.types[top] = "transform"
            self.types[top + "|" + top.strip("|") + "Shape"] = "mesh"
            self.parents[top + "|" + top.strip("|") + "Shape"] = top
        self.modified = True

    def polyEvaluate(self, shape, vertex=False, face=False, triangle=False):
        return 8 if vertex else 12 if triangle else 6

    def exactWorldBoundingBox(self, root):
        return [-1, 0, -1, 1, 2, 1]

    def currentUnit(self, query, linear):
        return "cm"

    def upAxis(self, query, axis):
        return "y"


@pytest.fixture
def model(tmp_path):
    fbx = tmp_path / "Orb Keeper.fbx"
    fbx.write_bytes(b"fbx")
    for suffix in ("", "_normal", "_metallic", "_roughness"):
        (tmp_path / "Orb Keeper{}.png".format(suffix)).write_bytes(b"png")
    return fbx


def test_texture_set_and_names(model):
    found = meshy_import.meshy_texture_set(str(model))
    assert sorted(found) == ["base_color", "metallic", "normal", "roughness"]
    assert meshy_import.node_name("Orb Keeper") == "Orb_Keeper"
    assert meshy_import.node_name("3d-model") == "Meshy_3d_model"


def test_import_groups_new_nodes_and_wires_a_standard_surface(model):
    cmds = FakeCmds()
    result = meshy_import.import_model(cmds, str(model))
    assert result["success"], result
    ctx = result["context"]
    assert ctx["group"] == "Orb_Keeper" and cmds.parents["|Body"] == "Orb_Keeper"
    assert "fbxmaya" in cmds.plugins
    assert [c for c in cmds.chunks if "openChunk" in c] and cmds.chunks[-1] == {"closeChunk": True}

    links = set(cmds.links)
    assert ("Orb_Keeper_base_color.outColor", "Orb_Keeper_mat.baseColor") in links
    assert ("Orb_Keeper_metallic.outColorR", "Orb_Keeper_mat.metalness") in links
    assert ("Orb_Keeper_roughness.outColorR", "Orb_Keeper_mat.specularRoughness") in links
    assert ("Orb_Keeper_normal.outAlpha", "Orb_Keeper_normal_bump2d.bumpValue") in links
    assert cmds.attrs["Orb_Keeper_normal_bump2d.bumpInterp"] == 1
    assert cmds.attrs["Orb_Keeper_base_color.colorSpace"] == "sRGB"
    for role in ("metallic", "roughness", "normal"):
        assert cmds.attrs["Orb_Keeper_{}.colorSpace".format(role)] == "Raw"
        assert cmds.attrs["Orb_Keeper_{}.ignoreColorSpaceFileRules".format(role)] is True
    assert cmds.members["Orb_Keeper_matSG"] == ["|Body|BodyShape"]

    readback = ctx["model"]
    assert readback["meshes"][0]["materials"] == ["Orb_Keeper_mat"]
    inputs = readback["materials"][0]["inputs"]
    assert inputs["metalness"]["output"] == "outColorR" and inputs["metalness"]["color_space"] == "Raw"
    assert inputs["normalCamera"]["use_as"] == 1 and inputs["normalCamera"]["exists"] is True
    assert readback["bounds"]["size"] == [2.0, 2.0, 2.0]
    assert ctx["scene_modified"] is True


def test_packed_map_follows_gltf_channels(tmp_path):
    fbx = tmp_path / "axe.fbx"
    fbx.write_bytes(b"fbx")
    packed = tmp_path / "axe_metallic_roughness.png"
    packed.write_bytes(b"png")
    cmds = FakeCmds()
    result = meshy_import.import_model(cmds, str(fbx), textures={"metallic_roughness": str(packed)})
    assert result["success"], result
    links = set(cmds.links)
    assert ("axe_metallic_roughness.outColorB", "axe_mat.metalness") in links
    assert ("axe_metallic_roughness.outColorG", "axe_mat.specularRoughness") in links


def test_existing_name_and_bad_inputs_are_refused(model, tmp_path):
    cmds = FakeCmds()
    cmds.types["Orb_Keeper"] = "transform"
    result = meshy_import.import_model(cmds, str(model))
    assert not result["success"] and "already exists" in result["message"]
    assert cmds.chunks == []
    assert not meshy_import.import_model(cmds, "relative.fbx")["success"]
    glb = tmp_path / "m.glb"
    glb.write_bytes(b"glb")
    assert "glTF" in meshy_import.import_model(cmds, str(glb))["error"]
    assert not meshy_import.import_model(cmds, str(model), name="x", textures={"albedo": str(model)})["success"]


def test_import_that_adds_nothing_is_an_error(model):
    result = meshy_import.import_model(FakeCmds(imported=()), str(model))
    assert not result["success"] and "added nothing" in result["message"]


def test_inspect_unknown_node():
    assert not meshy_import.inspect_model(FakeCmds(), node="Nope")["success"]


def test_skill_scripts_delegate(model, monkeypatch):
    import importlib.util
    import sys
    import types

    cmds = FakeCmds()
    maya = types.ModuleType("maya")
    maya.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    scripts = os.path.join(os.path.dirname(meshy_import.__file__), "skills", "meshy-maya", "scripts")
    spec = importlib.util.spec_from_file_location("meshy_maya_import_model", os.path.join(scripts, "import_model.py"))
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    assert script.main(source_path=str(model), name="Keeper")["success"]
