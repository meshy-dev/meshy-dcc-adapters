"""The release package layout, without downloads or a Houdini."""

from __future__ import annotations

import importlib.util
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _build_package():
    spec = importlib.util.spec_from_file_location("build_package", ROOT / "packaging" / "build_package.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_houdini_files_hook_every_candidate_python_and_ship_the_shelf(tmp_path):
    pkg = _build_package()
    pkg.stage_houdini_files(tmp_path / "houdini")
    hooks = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("uiready.py"))
    assert hooks == ["houdini/python3.{}libs/uiready.py".format(minor) for minor in pkg.STARTUP_PYTHON_MINORS]
    shelf = ET.parse(tmp_path / "houdini" / "toolbar" / "meshy_dcc.shelf").getroot()
    assert {tool.get("name") for tool in shelf.iter("tool")} >= {"meshy_dcc_houdini_start", "meshy_dcc_houdini_stop"}
    # No 123.py / 456.py: Houdini runs only the first one on its path, which would hide the user's own.
    assert not list(tmp_path.rglob("123.py")) and not list(tmp_path.rglob("456.py"))


@pytest.mark.parametrize(
    ("name", "platform", "error"),
    [
        ("meshy_dcc_core-0.2.0-cp38-abi3-macosx_11_0_arm64.whl", "macos-arm64", None),
        ("meshy_dcc_core-0.2.0-cp38-abi3-win_amd64.whl", "windows-x64", None),
        ("meshy_dcc_core-0.2.0-cp38-abi3-win_amd64.whl", "macos-arm64", "not built for"),
        ("meshy_dcc_core-0.3.0-cp38-abi3-macosx_11_0_arm64.whl", "macos-arm64", "need meshy_dcc_core"),
        ("other_core-0.2.0-cp38-abi3-macosx_11_0_arm64.whl", "macos-arm64", "not a meshy_dcc_core"),
    ],
)
def test_core_wheel_must_match_the_range_and_platform(name, platform, error):
    pkg = _build_package()
    if error is None:
        pkg.check_core_wheel(Path(name), platform)
    else:
        with pytest.raises(SystemExit, match=error):
            pkg.check_core_wheel(Path(name), platform)


def test_launchers_run_the_registration_script_isolated():
    pkg = _build_package()
    script = "lib/meshy_dcc_houdini/houdini_package.py"
    assert (ROOT / "src" / "meshy_dcc_houdini" / "houdini_package.py").is_file()
    assert '-I "$here/../{}"'.format(script) in pkg.POSIX_LAUNCHER
    assert '-I "%~dp0..\\{}"'.format(script.replace("/", "\\")) in pkg.WINDOWS_LAUNCHER
    assert pkg.WINDOWS_LAUNCHER.endswith("exit /b %ERRORLEVEL%\r\n")


def test_zip_is_reproducible_and_keeps_the_launcher_executable(tmp_path):
    pkg = _build_package()
    stage = tmp_path / "stage"
    (stage / "bin").mkdir(parents=True)
    launcher = stage / "bin" / "meshy-dcc-houdini"
    launcher.write_text(pkg.POSIX_LAUNCHER, encoding="utf-8")
    launcher.chmod(0o755)
    (stage / "lib.txt").write_text("x", encoding="utf-8")
    first, second = tmp_path / "a.zip", tmp_path / "b.zip"
    pkg.write_zip(stage, first)
    pkg.write_zip(stage, second)
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as bundle:
        mode = bundle.getinfo("bin/meshy-dcc-houdini").external_attr >> 16
    assert stat.S_IMODE(mode) == 0o755


def test_bundled_python_keeps_the_interpreter_and_stdlib_only(tmp_path):
    pkg = _build_package()
    home = tmp_path / "python"
    for name in (
        "bin/python3.11",
        "bin/pip",
        "lib/libpython3.11.dylib",
        "lib/libtcl9.0.dylib",
        "lib/python3.11/json/__init__.py",
        "lib/python3.11/site-packages/pip/__init__.py",
    ):
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_text("x", encoding="utf-8")
    (home / "bin" / "python3").symlink_to("python3.11")
    copy = tmp_path / "copy"
    pkg.shutil.copytree(home, copy, symlinks=False, ignore=pkg.ignore_python_files)
    kept = sorted(p.relative_to(copy).as_posix() for p in copy.rglob("*") if p.is_file())
    assert kept == ["bin/python3.11", "lib/python3.11/json/__init__.py"]
