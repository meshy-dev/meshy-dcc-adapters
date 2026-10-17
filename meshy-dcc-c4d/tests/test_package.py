import importlib.util
from pathlib import Path

import pytest

from meshy_dcc_c4d.__version__ import __version__

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("build_package", ROOT / "packaging" / "build_package.py")
build_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_package)


def test_version_metadata_is_synchronized():
    assert build_package.adapter_version() == __version__


def test_build_refuses_a_core_wheel_for_another_platform(tmp_path):
    wheel = tmp_path / "meshy_dcc_core-0.2.0-cp38-abi3-macosx_11_0_arm64.whl"
    with pytest.raises(SystemExit, match="win_amd64"):
        build_package.build(wheel, "windows-x64", tmp_path, None)


def test_windows_launcher_keeps_quotes_and_crlf():
    assert build_package.CMD.endswith("%*\r\n")
    assert '"%~dp0..\\python\\python.exe" -I -m meshy_dcc_c4d' in build_package.CMD
