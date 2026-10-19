"""The Windows package: a .cmd launcher next to a bundled python.exe."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "packaging" / "build_package.py"
spec = importlib.util.spec_from_file_location("build_package", SCRIPT)
build_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_package)


def test_cmd_launcher_runs_the_bundled_python_with_every_argument():
    text = build_package.SIDECAR_CMD
    assert text.startswith("@echo off\r\n")
    assert '"%~dp0..\\python\\python.exe" -m meshy_dcc_unity %*\r\n' in text
    assert "\n" not in text.replace("\r\n", "")


def test_a_python_exe_at_the_root_marks_a_windows_install(tmp_path: Path):
    assert not build_package.is_windows_python(tmp_path)
    assert build_package.platform_tag(tmp_path) != "windows_x86_64"
    (tmp_path / "python.exe").write_bytes(b"")
    assert build_package.is_windows_python(tmp_path)
    assert build_package.platform_tag(tmp_path) == "windows_x86_64"


def test_editor_runs_a_cmd_launcher_through_cmd_exe():
    source = (
        ROOT / "src" / "meshy_dcc_unity" / "unity_package" / "Editor" / "MeshyDccSidecarLauncher.cs"
    ).read_text(encoding="utf-8")
    assert 'Path.Combine(Environment.SystemDirectory, "cmd.exe")' in source
    assert '"/d /s /c \\"\\"" + path + "\\" " + arguments + "\\""' in source
