"""Exercise the actual editor command boundary in a disposable headless project."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
GODOT = os.environ.get("GODOT_TEST_EXECUTABLE")


@pytest.mark.skipif(not GODOT, reason="set GODOT_TEST_EXECUTABLE for the real editor regression")
def test_scene_property_values_are_validated_applied_and_read_back(tmp_path: Path):
    project = tmp_path / "project"
    addon = ROOT / "src/meshy_dcc_godot/godot_addon/addons/meshy_dcc_godot"
    shutil.copytree(addon, project / "addons/meshy_dcc_godot")
    driver = project / "addons/property_test"
    driver.mkdir()
    shutil.copy2(ROOT / "tests/godot_project/scene_property_smoke.gd", driver / "plugin.gd")
    (driver / "plugin.cfg").write_text(
        '[plugin]\nname="Property regression"\ndescription="Disposable test"\n'
        'author="Meshy"\nversion="1"\nscript="plugin.gd"\n',
        encoding="utf-8",
    )
    (project / "project.godot").write_text(
        'config_version=5\n[application]\nconfig/name="Property regression"\n'
        '[editor_plugins]\nenabled=PackedStringArray("res://addons/property_test/plugin.cfg")\n'
        '[rendering]\nrenderer/rendering_method="gl_compatibility"\n',
        encoding="utf-8",
    )
    (project / "main.tscn").write_text(
        '[gd_scene format=3]\n[node name="Main" type="Node3D"]\n'
        '[node name="RedBox" type="Node3D" parent="."]\nposition=Vector3(9, 8, 7)\n',
        encoding="utf-8",
    )
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
        timeout=60,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "SCENE_PROPERTY_SMOKE_OK" in output, output
