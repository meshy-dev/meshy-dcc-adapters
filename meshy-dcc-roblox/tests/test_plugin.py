"""Checks of the Studio plugin that need no Studio: names, ports, static analysis."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from meshy_dcc_roblox import __version__

PACKAGE = Path(__file__).parents[1] / "src" / "meshy_dcc_roblox"
PLUGIN = PACKAGE / "plugin" / "MeshyDcc.lua"
# Globals and types that Studio provides and plain Luau does not know.
ROBLOX_NAMES = (
    "game|workspace|plugin|task|Enum|Instance|Vector3|Vector2|CFrame|Color3|BrickColor|"
    "Content|version|loadstring|EditableMesh|EditableImage|SurfaceAppearance"
)


def tool_names():
    names = set()
    for tools in PACKAGE.glob("skills/*/tools.yaml"):
        for tool in yaml.safe_load(tools.read_text(encoding="utf-8"))["tools"]:
            if tool["source_file"] == "scripts/dispatch.py":
                names.add(tool["name"])
    return names


def test_every_dispatched_tool_has_a_plugin_handler():
    source = PLUGIN.read_text(encoding="utf-8")
    handlers = set(re.findall(r"^handlers\.(\w+) = function", source, re.MULTILINE))
    handlers |= set(re.findall(r'^handlers\["([\w.]+)"\] = function', source, re.MULTILINE))
    assert tool_names() <= handlers
    assert {"meshy.import_begin", "meshy.import_data", "meshy.import_finish"} <= handlers


def test_plugin_version_and_marker_match_the_package():
    from meshy_dcc_roblox.install import PLUGIN_MARKER

    first, *_ = PLUGIN.read_text(encoding="utf-8").splitlines()
    assert first.startswith(f"{PLUGIN_MARKER} {__version__}")
    assert f'local VERSION = "{__version__}"' in PLUGIN.read_text(encoding="utf-8")


def test_luau_analyze_finds_nothing_but_studio_globals():
    analyzer = os.environ.get("LUAU_ANALYZE") or shutil.which("luau-analyze")
    if not analyzer:
        pytest.skip("luau-analyze from the official Luau release is not available")
    output = subprocess.run(
        [analyzer, "--formatter=plain", PLUGIN.name], cwd=PLUGIN.parent, capture_output=True, text=True
    )
    ignored = re.compile(rf"Unknown (global|type) '({ROBLOX_NAMES})'|Type inference failed to complete")
    issues = [line for line in (output.stdout + output.stderr).splitlines() if line and not ignored.search(line)]
    assert issues == []
