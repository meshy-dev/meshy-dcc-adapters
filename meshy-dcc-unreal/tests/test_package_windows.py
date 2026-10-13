"""The Windows package's installer launcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _build_package():
    spec = importlib.util.spec_from_file_location(
        "_test_packaging_build_package", Path(__file__).parents[1] / "packaging" / "build_package.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_launcher_quotes_its_paths_and_forwards_every_argument():
    module = _build_package()
    script = module.WINDOWS_INSTALLER_SCRIPT.format(plugin=module.PLUGIN_NAME)
    lines = script.split("\r\n")
    assert lines[0] == "@echo off" and script.endswith("\r\n") and "\n" not in script.replace("\r\n", "")
    assert 'set "PYTHONPATH=%~dp0..\\plugin\\MeshyDccUnreal\\python"' in lines
    assert '"%~dp0..\\python\\python.exe" -m meshy_dcc_unreal.install_cli %*' in lines
    assert lines[-2] == "exit /b %ERRORLEVEL%"
