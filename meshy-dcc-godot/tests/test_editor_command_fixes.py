"""Run the editor command fixes against a disposable headless project."""

import base64
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
GODOT = os.environ.get("GODOT_TEST_EXECUTABLE")
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/"
    "iZk9HQAAAABJRU5ErkJggg=="
)


@pytest.mark.skipif(not GODOT, reason="set GODOT_TEST_EXECUTABLE for the real editor regression")
def test_editor_commands_persist_validate_and_report_honestly(tmp_path: Path):
    project = tmp_path / "project"
    shutil.copytree(
        ROOT / "src/meshy_dcc_godot/godot_addon/addons/meshy_dcc_godot",
        project / "addons/meshy_dcc_godot",
    )
    driver = project / "addons/command_test"
    driver.mkdir()
    shutil.copy2(ROOT / "tests/godot_project/editor_command_smoke.gd", driver / "plugin.gd")
    (driver / "plugin.cfg").write_text(
        '[plugin]\nname="Command regression"\ndescription="Disposable test"\n'
        'author="Meshy"\nversion="1"\nscript="plugin.gd"\n',
        encoding="utf-8",
    )
    (project / "project.godot").write_text(
        'config_version=5\n[application]\nconfig/name="Command regression"\n'
        '[editor_plugins]\nenabled=PackedStringArray("res://addons/command_test/plugin.cfg")\n'
        '[rendering]\nrenderer/rendering_method="gl_compatibility"\n',
        encoding="utf-8",
    )
    (project / "main.tscn").write_text(
        '[gd_scene format=3]\n[node name="Main" type="Node3D"]\n', encoding="utf-8"
    )
    (project / "ok.gd").write_text("extends Node\n", encoding="utf-8")
    (project / "icon.png").write_bytes(PNG)
    env = dict(os.environ)
    env.update(
        HOME=str(tmp_path / "home"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        XDG_CONFIG_HOME=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        MESHY_DCC_TELEMETRY="0",
        MESHY_DCC_DISABLE_UPDATE_CHECK="1",
    )
    result = subprocess.run(
        [GODOT, "--headless", "--editor", "--path", str(project)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "EDITOR_COMMAND_SMOKE_OK" in output, output
