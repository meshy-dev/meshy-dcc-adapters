"""meshy-unreal skill: the parts that do not need a running editor."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

SKILL = Path(__file__).resolve().parents[1] / "src" / "meshy_dcc_unreal" / "skills" / "meshy-unreal"


@pytest.fixture
def scripts(monkeypatch):
    monkeypatch.syspath_prepend(str(SKILL / "scripts"))
    monkeypatch.setitem(sys.modules, "unreal", SimpleNamespace())
    for name in ("_meshy", "import_model", "capture_model"):
        sys.modules.pop(name, None)
    return SimpleNamespace(
        meshy=importlib.import_module("_meshy"),
        importer=importlib.import_module("import_model"),
        capture=importlib.import_module("capture_model"),
    )


def error_of(result: dict) -> str:
    assert result["success"] is False
    return result["message"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("breeze_scout", "breeze_scout"), ("Orb Keeper (1)", "Orb_Keeper_1"), ("3d-model", "M_3d_model")],
)
def test_asset_names_are_content_browser_safe(scripts, raw, expected):
    assert scripts.meshy.asset_name(raw) == expected


def test_the_meshy_texture_set_is_found_next_to_the_fbx(scripts, tmp_path):
    for suffix in ("", "_normal", "_roughness"):
        (tmp_path / f"orb_texture{suffix}.png").write_bytes(b"")
    found = scripts.importer.meshy_texture_set(str(tmp_path / "orb_texture.fbx"))
    assert found == {
        "base_color": str(tmp_path / "orb_texture.png"),
        "normal": str(tmp_path / "orb_texture_normal.png"),
        "roughness": str(tmp_path / "orb_texture_roughness.png"),
    }


def test_import_rejects_bad_arguments_before_touching_the_editor(scripts, tmp_path):
    model = tmp_path / "orb.fbx"
    model.write_bytes(b"")
    image = tmp_path / "orb.png"
    image.write_bytes(b"")
    run = scripts.importer.import_model
    assert "absolute" in error_of(run(source_path="orb.fbx"))
    assert "format" in error_of(run(source_path=str(tmp_path / "orb.png")))
    assert "roles" in error_of(run(source_path=str(model), textures={"albedo": str(image)}))
    assert "textures.normal" in error_of(run(source_path=str(model), textures={"normal": str(model)}))


def test_capture_views_match_the_tool_schema(scripts):
    tools = {tool["name"]: tool for tool in yaml.safe_load((SKILL / "tools.yaml").read_text())["tools"]}
    views = tools["capture_model"]["input_schema"]["properties"]["view"]["enum"]
    assert views == list(scripts.capture.VIEWS)
    # An imported Meshy model faces +Y: the front camera sits on +Y.
    assert scripts.capture.VIEWS["front"][:2] == (0.0, 1.0)
