"""The package installer writes and removes only its own startup script."""

from __future__ import annotations

import base64
import json
import re

import pytest

from meshy_dcc_3dsmax import host_install

DCC = "C:/Program Files/Autodesk/3ds Max 2026/3dsmax.exe"


@pytest.fixture
def home(tmp_path):
    """A LOCALAPPDATA where 3ds Max 2026 was started in English and Chinese."""
    root = tmp_path / "Local" / "Autodesk" / "3dsMax" / "2026 - 64bit"
    (root / "ENU" / "scripts" / "startup").mkdir(parents=True)
    (root / "CHS" / "scripts").mkdir(parents=True)
    (root / "ENU" / "usermacros").mkdir()
    (root / "ENU" / "usermacros" / "Meshy DCC-MeshyDcc3dsmax_StopSidecar.mcr").write_text("macro")
    (root / "ENU" / "usermacros" / "Other-Tool.mcr").write_text("user macro")
    payload = tmp_path / "pkg dir" / "payload"
    (payload / "meshy_dcc_3dsmax").mkdir(parents=True)
    (payload / "meshy_dcc_core").mkdir()
    return {"env": {"LOCALAPPDATA": str(tmp_path / "Local")}, "root": root, "payload": payload}


def test_year_comes_from_the_install_folder():
    assert host_install.max_year(DCC) == "2026"
    assert host_install.max_year(r"D:\Autodesk\3ds Max 2025\3dsmax.exe") == "2025"
    with pytest.raises(host_install.InstallError, match="version"):
        host_install.max_year(r"D:\Apps\Max\3dsmax.exe")


def test_install_writes_every_language_and_uninstall_removes_only_its_files(home):
    result = host_install.install(DCC, env=home["env"], payload=home["payload"])
    scripts = [home["root"] / lang / "scripts" / "startup" / host_install.STARTUP_SCRIPT_NAME for lang in ("CHS", "ENU")]
    assert result["startup_scripts"] == [str(path) for path in scripts]
    text = scripts[1].read_bytes().decode("ascii")
    assert text.startswith(host_install.MARKER) and "\r\n" in text
    encoded = re.search(r"b64decode\('([^']+)'\)", text).group(1)
    assert base64.b64decode(encoded).decode("utf-8") == str(home["payload"])
    assert text.count('"') == 2  # one MAXScript string literal, nothing to escape inside

    again = host_install.install(DCC, env=home["env"], payload=home["payload"])  # reinstall overwrites its own
    assert again["ok"]

    removed = host_install.uninstall(DCC, env=home["env"])["removed"]
    assert not any(path.exists() for path in scripts)
    assert str(home["root"] / "ENU" / "usermacros" / "Meshy DCC-MeshyDcc3dsmax_StopSidecar.mcr") in removed
    assert (home["root"] / "ENU" / "usermacros" / "Other-Tool.mcr").exists()
    assert host_install.uninstall(DCC, env=home["env"])["removed"] == []


def test_install_refuses_a_foreign_script_and_a_host_never_started(home, tmp_path):
    foreign = home["root"] / "ENU" / "scripts" / "startup" / host_install.STARTUP_SCRIPT_NAME
    foreign.write_text("-- someone else's file")
    with pytest.raises(host_install.InstallError) as refused:
        host_install.install(DCC, env=home["env"], payload=home["payload"])
    assert refused.value.code == "startup_script_foreign"
    assert foreign.read_text() == "-- someone else's file"
    assert host_install.uninstall(DCC, env=home["env"])["warnings"]
    assert foreign.exists()

    with pytest.raises(host_install.InstallError) as never:
        host_install.install(DCC.replace("2026", "2025"), env=home["env"], payload=home["payload"])
    assert never.value.code == "host_never_started"


def test_install_warns_when_the_original_adapter_is_installed(home):
    (home["root"] / "ENU" / "scripts" / "startup" / "dcc_mcp_3dsmax_startup.ms").write_text("upstream")
    result = host_install.install(DCC, env=home["env"], payload=home["payload"])
    assert len(result["warnings"]) == 1


def test_cli_prints_one_json_object_and_exits_with_the_error_code(home, monkeypatch, capsys):
    monkeypatch.setenv("LOCALAPPDATA", home["env"]["LOCALAPPDATA"])
    code = host_install.main(["install", "--dcc-path", r"D:\Apps\Max\3dsmax.exe", "--yes", "--json"])
    report = json.loads(capsys.readouterr().out)
    assert code == host_install.EXIT_PREFLIGHT
    assert report["ok"] is False and report["error"]["code"] == "dcc_version_unknown"


def test_installer_runs_on_the_standard_library_alone():
    """The package runs host_install.py with ``python -I``: no meshy_dcc_core, no package import."""
    import ast
    import sys
    from pathlib import Path

    tree = ast.parse(Path(host_install.__file__).read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}


def test_windows_launcher_runs_the_installer_isolated_and_forwards_every_argument():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("_build_package", Path(__file__).parents[1] / "packaging" / "build_package.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    script = module.INSTALLER_SCRIPT
    lines = script.split("\r\n")
    assert lines[0] == "@echo off" and script.endswith("\r\n") and "\n" not in script.replace("\r\n", "")
    assert '"%~dp0..\\python\\python.exe" -I "%~dp0..\\payload\\meshy_dcc_3dsmax\\host_install.py" %*' in lines
    assert lines[-2] == "exit /b %ERRORLEVEL%"
    assert module.PACKAGE_NAME == "meshy-dcc-3dsmax-windows-x64.zip"
