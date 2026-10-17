"""The package registration that meshy-dcc install runs, without Houdini."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from meshy_dcc_houdini import houdini_package as hp

MAC_HOUDINI = (
    "/Applications/Houdini/Houdini21.0.440/Frameworks/Houdini.framework/Versions/Current/Resources/bin/houdini"
)
WIN_HOUDINI = "C:/Program Files/Side Effects Software/Houdini 20.5.613/bin/houdini.exe"


@pytest.mark.parametrize(
    ("path", "version"),
    [
        (MAC_HOUDINI, "21.0"),
        ("/Applications/Houdini/Houdini21.0.440/Houdini FX 21.0.440.app/Contents/MacOS/houdini", "21.0"),
        ("/opt/x/Houdini.framework/Versions/22.0/Resources/bin/houdini", "22.0"),
        (WIN_HOUDINI, "20.5"),
        ("C:\\Program Files\\Side Effects Software\\Houdini 20.5.613\\bin\\houdini.exe", "20.5"),
    ],
)
def test_version_comes_from_the_install_path(path, version):
    assert hp.houdini_version(path, {}) == version


def test_version_follows_a_current_link(tmp_path):
    real = tmp_path / "Houdini21.0.440" / "bin"
    real.mkdir(parents=True)
    (real / "houdini").write_text("")
    (tmp_path / "Current").symlink_to(tmp_path / "Houdini21.0.440")
    assert hp.houdini_version(str(tmp_path / "Current" / "bin" / "houdini"), {}) == "21.0"


def test_version_override_and_unknown_path():
    assert hp.houdini_version("/games/steam/houdini", {hp.VERSION_ENV: "20.5"}) == "20.5"
    with pytest.raises(hp.PackageError, match=hp.VERSION_ENV):
        hp.houdini_version("/games/steam/houdini", {})
    with pytest.raises(hp.PackageError, match="MAJOR.MINOR"):
        hp.houdini_version(MAC_HOUDINI, {hp.VERSION_ENV: "21"})


def test_user_pref_dir_follows_houdini_rules(tmp_path):
    home = str(tmp_path)
    assert hp.user_pref_dir("21.0", {"HOME": home}, "darwin") == tmp_path / "Library/Preferences/houdini/21.0"
    assert hp.user_pref_dir("20.5", {"HOME": home}, "win32") == tmp_path / "houdini20.5"
    # Without HOME, Windows Houdini uses the Documents folder.
    documents = hp.user_pref_dir("20.5", {"USERPROFILE": home}, "win32")
    assert documents.name == "houdini20.5" and documents.parent.name == "Documents"
    override = {"HOME": home, "HOUDINI_USER_PREF_DIR": str(tmp_path / "prefs" / "houdini__HVER__")}
    assert hp.user_pref_dir("21.0", override, "darwin") == tmp_path / "prefs" / "houdini21.0"
    with pytest.raises(hp.PackageError, match="__HVER__"):
        hp.user_pref_dir("21.0", {"HOUDINI_USER_PREF_DIR": home}, "win32")


def _package(tmp_path: Path) -> Path:
    root = tmp_path / "adapters" / "meshy-dcc-houdini-macos-arm64"
    (root / "houdini").mkdir(parents=True)
    (root / "lib" / "meshy_dcc_houdini").mkdir(parents=True)
    return root


def test_install_writes_one_package_file_and_uninstall_removes_only_its_own(tmp_path):
    root = _package(tmp_path)
    environ = {"HOME": str(tmp_path / "home")}
    result = hp.install(MAC_HOUDINI, root, environ, "darwin")
    target = tmp_path / "home/Library/Preferences/houdini/21.0/packages" / hp.PACKAGE_FILE
    assert result == {
        "status": "installed",
        "houdini_version": "21.0",
        "package_file": str(target),
        "package_root": str(root),
    }
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["env"][0] == {hp.ROOT_ENV: root.as_posix()}
    assert document["env"][1]["PYTHONPATH"] == {"method": "prepend", "value": "$MESHY_DCC_HOUDINI_ROOT/lib"}
    assert document["hpath"] == "$MESHY_DCC_HOUDINI_ROOT/houdini"
    assert [p.name for p in target.parent.iterdir()] == [hp.PACKAGE_FILE]

    # A reinstall from another extracted copy takes the registration over.
    other = _package(tmp_path / "other")
    hp.install(MAC_HOUDINI, other, environ, "darwin")
    assert hp.uninstall(MAC_HOUDINI, root, environ, "darwin")["status"] == "kept"
    assert target.exists()
    assert hp.uninstall(MAC_HOUDINI, other, environ, "darwin")["status"] == "removed"
    assert not target.exists()
    assert hp.uninstall(MAC_HOUDINI, other, environ, "darwin")["status"] == "not_installed"


def test_install_refuses_a_directory_that_is_not_a_package(tmp_path):
    with pytest.raises(hp.PackageError, match="not an extracted"):
        hp.install(MAC_HOUDINI, tmp_path, {"HOME": str(tmp_path)}, "darwin")


def test_cli_reports_json_and_failures(tmp_path, monkeypatch, capsys):
    root = _package(tmp_path)
    monkeypatch.setattr(hp, "package_root", lambda: root)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("HOUDINI_USER_PREF_DIR", raising=False)
    monkeypatch.delenv(hp.VERSION_ENV, raising=False)
    assert hp.main(["install", "--dcc-path", WIN_HOUDINI, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["houdini_version"] == "20.5"
    assert hp.main(["uninstall", "--dcc-path", WIN_HOUDINI, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "removed"
    assert hp.main(["install", "--dcc-path", "/unknown/houdini", "--json"]) == 1
    assert hp.VERSION_ENV in capsys.readouterr().err


def test_registration_runs_on_the_standard_library_alone():
    tree = ast.parse(Path(hp.__file__).read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}
