from __future__ import annotations

import json
from pathlib import Path

import pytest

from meshy_dcc_material_maker.bridge import MaterialMakerCli, MaterialMakerError

MATERIAL = {
    "type": "material_export",
    "shader_model": {
        "inputs": [{"name": n, "type": "rgb"} for n in ("albedo_tex", "metallic_tex", "roughness_tex")],
        "outputs": [],
        "parameters": [
            {"name": "albedo_color", "type": "color", "default": {"r": 1, "g": 1, "b": 1, "a": 1}},
            {"name": "metallic", "type": "float", "default": 1, "min": 0, "max": 1},
        ],
        "exports": {
            "Godot/Godot 4 Standard": {"files": [{"type": "texture", "file_name": "$(path_prefix)_albedo.png"}]},
            "Unreal/Unreal Engine 5": {"files": [{"type": "template", "file_name": "clipboard"}]},
        },
    },
}
PERLIN = {
    "type": "shader",
    "shader_model": {
        "shortdesc": "Value Noise",
        "inputs": [],
        "outputs": [{"type": "f"}],
        "parameters": [
            {"name": "scale_x", "type": "float", "default": 4},
            {"name": "mode", "type": "enum", "default": 0, "values": [{"name": "a"}, {"name": "b"}]},
        ],
    },
}


@pytest.fixture
def cli(tmp_path) -> MaterialMakerCli:
    install = tmp_path / "mm"
    (install / "nodes").mkdir(parents=True)
    (install / "examples").mkdir()
    (install / "nodes" / "material.mmg").write_text(json.dumps(MATERIAL), encoding="utf-8")
    (install / "nodes" / "perlin.mmg").write_text(json.dumps(PERLIN), encoding="utf-8")
    executable = install / "material_maker"
    executable.write_bytes(b"fixture")
    example = {
        "type": "graph",
        "nodes": [{"name": "Material", "type": "material", "parameters": {}}],
        "connections": [],
    }
    (install / "examples" / "plain.ptex").write_text(json.dumps(example), encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    return MaterialMakerCli(str(executable), allowed_roots=[project])


def test_blank_material_is_built_up_by_typed_edits(cli):
    created = cli.create_material("materials/stone.ptex")
    assert [n["type"] for n in created["nodes"]] == ["material"]
    edited = cli.edit_graph(
        "materials/stone.ptex",
        [
            {"op": "add_node", "name": "Noise", "type": "perlin", "parameters": {"scale_x": 8}},
            {"op": "connect", "from": "Noise", "from_port": 0, "to": "Material", "to_port": 2},
            {"op": "set_parameters", "node": "Material", "parameters": {"albedo_color": {"r": 0.5, "g": 0.4, "b": 0.3}}},
        ],
        expected_sha256=created["sha256"],
    )
    assert edited["previous_sha256"] == created["sha256"]
    graph = cli.get_graph("materials/stone.ptex")
    assert graph["sha256"] == edited["sha256"]
    nodes = {n["name"]: n for n in graph["nodes"]}
    assert nodes["Noise"]["parameters"] == {"scale_x": 8}
    assert nodes["Material"]["parameters"]["albedo_color"] == {"r": 0.5, "g": 0.4, "b": 0.3, "a": 1, "type": "Color"}
    assert graph["connections"] == [{"from": "Noise", "from_port": 0, "to": "Material", "to_port": 2}]
    # The file is Material Maker's own layout: tab-indented, sorted keys.
    text = (cli.project_root / "materials" / "stone.ptex").read_text(encoding="utf-8")
    assert text.startswith('{\n\t"connections"')


def test_connect_replaces_the_previous_source_and_remove_drops_links(cli):
    cli.create_material("m.ptex")
    cli.edit_graph(
        "m.ptex",
        [
            {"op": "add_node", "name": "A", "type": "perlin"},
            {"op": "add_node", "name": "B", "type": "perlin"},
            {"op": "connect", "from": "A", "from_port": 0, "to": "Material", "to_port": 0},
            {"op": "connect", "from": "B", "from_port": 0, "to": "Material", "to_port": 0},
        ],
    )
    assert cli.get_graph("m.ptex")["connections"] == [{"from": "B", "from_port": 0, "to": "Material", "to_port": 0}]
    cli.edit_graph("m.ptex", [{"op": "remove_node", "node": "B"}])
    graph = cli.get_graph("m.ptex")
    assert graph["connections"] == [] and {n["name"] for n in graph["nodes"]} == {"Material", "A"}


@pytest.mark.parametrize(
    "operation, message",
    [
        ({"op": "add_node", "name": "Cam", "type": "webcam"}, "Unknown node type"),
        ({"op": "add_node", "name": "1bad", "type": "perlin"}, "name must be"),
        ({"op": "add_node", "name": "Material", "type": "perlin"}, "already exists"),
        ({"op": "set_parameters", "node": "Material", "parameters": {"nope": 1}}, "has no parameter nope"),
        ({"op": "set_parameters", "node": "Material", "parameters": {"metallic": "1"}}, "must be a number"),
        ({"op": "set_parameters", "node": "Material", "parameters": {"albedo_color": "red"}}, "must be a color"),
        ({"op": "connect", "from": "Ok", "from_port": 0, "to": "Material", "to_port": 9}, "has 3 inputs"),
        ({"op": "connect", "from": "Material", "from_port": 0, "to": "Ok", "to_port": 0}, "has 0 outputs"),
        ({"op": "remove_node", "node": "Ghost"}, "No node named Ghost"),
        ({"op": "explode"}, "op must be"),
    ],
)
def test_rejected_operation_leaves_the_file_unchanged(cli, operation, message):
    created = cli.create_material("m.ptex")
    before = (cli.project_root / "m.ptex").read_bytes()
    with pytest.raises(MaterialMakerError, match=message):
        cli.edit_graph("m.ptex", [{"op": "add_node", "name": "Ok", "type": "perlin"}, operation])
    assert (cli.project_root / "m.ptex").read_bytes() == before
    assert cli.get_graph("m.ptex")["sha256"] == created["sha256"]


def test_enum_parameters_take_an_index(cli):
    cli.create_material("m.ptex")
    cli.edit_graph("m.ptex", [{"op": "add_node", "name": "N", "type": "perlin", "parameters": {"mode": 1}}])
    with pytest.raises(MaterialMakerError, match="index into"):
        cli.edit_graph("m.ptex", [{"op": "set_parameters", "node": "N", "parameters": {"mode": 2}}])


def test_edit_refuses_a_file_that_changed_since_it_was_read(cli):
    created = cli.create_material("m.ptex")
    cli.edit_graph("m.ptex", [{"op": "add_node", "name": "N", "type": "perlin"}])
    with pytest.raises(MaterialMakerError, match="changed since it was read"):
        cli.edit_graph("m.ptex", [{"op": "remove_node", "node": "N"}], expected_sha256=created["sha256"])


def test_image_nodes_read_only_project_images(cli, tmp_path):
    (cli.project_root / "textures").mkdir()
    (cli.project_root / "textures" / "base.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "outside.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    cli.create_material("m.ptex")
    cli.edit_graph(
        "m.ptex",
        [{"op": "add_node", "name": "Base", "type": "image", "parameters": {"image": "textures/base.png"}}],
    )
    node = cli.get_graph("m.ptex", node="Base")["nodes"][0]
    # Material Maker resolves relative paths against its install folder.
    assert node["parameters"]["image"] == str(cli.project_root / "textures" / "base.png")
    for path in (str(tmp_path / "outside.png"), "../outside.png", "textures/missing.png"):
        with pytest.raises(MaterialMakerError):
            cli.edit_graph("m.ptex", [{"op": "set_parameters", "node": "Base", "parameters": {"image": path}}])


def test_create_never_replaces_and_stays_in_the_project(cli):
    cli.create_material("m.ptex", template="plain")
    with pytest.raises(MaterialMakerError, match="already exists"):
        cli.create_material("m.ptex")
    with pytest.raises(MaterialMakerError, match="outside the project"):
        cli.create_material("../escape.ptex")
    with pytest.raises(MaterialMakerError, match="No example"):
        cli.create_material("n.ptex", template="missing")
    copy = cli.create_material("copy.ptex", source="m.ptex")
    assert copy["source"].endswith("m.ptex")


def test_graphs_reaching_the_camera_network_or_other_folders_are_invalid(cli):
    for node in (
        {"name": "Cam", "type": "webcam"},
        {"name": "Web", "type": "website:12"},
        {"name": "Out", "type": "export", "parameters": {"suffix": "../../x"}},
    ):
        graph = {"type": "graph", "nodes": [node], "connections": []}
        (cli.project_root / "bad.ptex").write_text(json.dumps(graph), encoding="utf-8")
        assert cli.validate_project("bad.ptex")["valid"] is False


def test_export_targets_follow_the_material_definition_without_clipboard_profiles(cli):
    assert cli.export_targets() == ["Godot/Godot 4 Standard"]
    graph = json.loads(json.dumps({"type": "graph", "nodes": [{"name": "Material", "type": "material"}], "connections": []}))
    assert cli._target(graph, "Godot") == "Godot/Godot 4 Standard"
    with pytest.raises(MaterialMakerError, match="target must be one of: Godot/Godot 4 Standard"):
        cli._target(graph, "Unreal/Unreal Engine 5")


def test_node_types_are_searchable_and_described(cli):
    found = cli.list_node_types(query="noise")
    assert found["node_types"] == [{"type": "perlin", "shortdesc": "Value Noise"}]
    described = cli.list_node_types(node_type="perlin")
    assert [p["name"] for p in described["parameters"]] == ["scale_x", "mode"]
    assert described["parameters"][1]["values"] == ["a", "b"]
    with pytest.raises(MaterialMakerError, match="Unknown node type"):
        cli.list_node_types(node_type="nope")


def test_status_lists_examples_and_needs_a_probe_to_be_ready(cli):
    status = cli.status()
    assert status["examples"] == ["plain"]
    assert status["node_type_count"] == 2
    assert status["ready"] is False and status["reason"] == "probe_project_required"


def test_app_bundle_path_resolves_to_its_executable(tmp_path):
    app = tmp_path / "Material Maker.app"
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    (macos / "Material Maker").write_bytes(b"fixture")
    cli = MaterialMakerCli(str(app), allowed_roots=[tmp_path])
    assert Path(cli.executable) == (macos / "Material Maker").resolve()


def test_open_in_material_maker_starts_a_detached_window_on_the_graph(cli, monkeypatch):
    from meshy_dcc_material_maker import bridge

    launched = []

    class FakePopen:
        def __init__(self, command, **options):
            launched.append((command, options))
            self.pid = 4242

    monkeypatch.setattr(bridge.subprocess, "Popen", FakePopen)
    created = cli.create_material("materials/m.ptex")
    opened = cli.open_in_material_maker("materials/m.ptex")
    (command, options), = launched
    # Material Maker opens a .ptex passed as an absolute path.
    assert command == [cli.executable, str(cli.project_root / "materials" / "m.ptex")]
    assert options["stdout"] is bridge.subprocess.DEVNULL
    assert options["stderr"] is bridge.subprocess.DEVNULL
    if bridge.os.name == "nt":
        assert options["creationflags"]
    else:
        assert options["start_new_session"] is True
    assert opened["pid"] == 4242 and opened["sha256"] == created["sha256"]
    assert "close" in opened["note"]


def test_open_in_material_maker_refuses_what_it_would_not_export(cli, monkeypatch):
    from meshy_dcc_material_maker import bridge

    monkeypatch.setattr(bridge.subprocess, "Popen", lambda *a, **k: pytest.fail("launched"))
    graph = {"type": "graph", "nodes": [{"name": "Cam", "type": "webcam"}], "connections": []}
    (cli.project_root / "cam.ptex").write_text(json.dumps(graph), encoding="utf-8")
    with pytest.raises(MaterialMakerError, match="failed validation"):
        cli.open_in_material_maker("cam.ptex")
    with pytest.raises(MaterialMakerError, match="does not exist|outside"):
        cli.open_in_material_maker("../elsewhere.ptex")
    cli.executable = None
    with pytest.raises(MaterialMakerError, match="not found"):
        cli.open_in_material_maker("cam.ptex")
