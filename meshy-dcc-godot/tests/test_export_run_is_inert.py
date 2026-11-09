"""An export run of a project with the add-on enabled must leave the open editor alone."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
GODOT = os.environ.get("GODOT_TEST_EXECUTABLE")


def _project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    shutil.copytree(
        ROOT / "src/meshy_dcc_godot/godot_addon/addons/meshy_dcc_godot",
        project / "addons/meshy_dcc_godot",
    )
    (project / "project.godot").write_text(
        'config_version=5\n[application]\nconfig/name="Export inert"\n'
        '[editor_plugins]\nenabled=PackedStringArray("res://addons/meshy_dcc_godot/plugin.cfg")\n'
        '[rendering]\nrenderer/rendering_method="gl_compatibility"\n',
        encoding="utf-8",
    )
    (project / "export_presets.cfg").write_text(
        '[preset.0]\nname="Linux"\nplatform="Linux"\nrunnable=true\nexport_path=""\n',
        encoding="utf-8",
    )
    marker = tmp_path / "sidecar-started"
    sidecar = tmp_path / "sidecar.sh"
    sidecar.write_text(f'#!/bin/sh\ntouch "{marker}"\n', encoding="utf-8")
    sidecar.chmod(sidecar.stat().st_mode | stat.S_IXUSR)
    (project / ".meshy-dcc").mkdir()
    (project / ".meshy-dcc/godot.json").write_text(
        json.dumps({"owner": "meshy-dcc-godot", "sidecar": str(sidecar)}), encoding="utf-8"
    )
    return project, marker


def _run(project: Path, tmp_path: Path, *args: str) -> None:
    env = {**os.environ, "HOME": str(tmp_path / "home")}
    for name in ("MESHY_DCC_GODOT_SIDECAR", "MESHY_DCC_GODOT_BRIDGE_URL"):
        env.pop(name, None)
    subprocess.run(
        [GODOT, "--headless", "--path", str(project), *args],
        env=env, capture_output=True, timeout=120, check=False,
    )


@pytest.mark.skipif(not GODOT, reason="set GODOT_TEST_EXECUTABLE for the real editor regression")
def test_export_run_starts_no_sidecar_and_changes_nothing(tmp_path: Path):
    project, marker = _project(tmp_path)
    settings_before = (project / "project.godot").read_bytes()

    _run(project, tmp_path, "--export-release", "Linux", str(tmp_path / "out" / "game"))

    assert not marker.exists()
    assert (project / "project.godot").read_bytes() == settings_before
    assert not (project / ".godot/meshy_dcc_godot_bootstrap.json").exists()


@pytest.mark.skipif(not GODOT, reason="set GODOT_TEST_EXECUTABLE for the real editor regression")
def test_editor_session_still_starts_the_sidecar(tmp_path: Path):
    """Control for the test above: the same project in an editor session does start it."""
    project, marker = _project(tmp_path)

    _run(project, tmp_path, "--editor", "--quit-after", "120")

    assert marker.exists()
