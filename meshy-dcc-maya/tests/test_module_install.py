"""The Meshy DCC installer writes and removes only its own .mod file."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from meshy_dcc_maya import __version__, module_install


def _module(tmp_path):
    module = tmp_path / "package" / "module"
    for item in module_install.REQUIRED:
        (module / item).parent.mkdir(parents=True, exist_ok=True)
        (module / item).write_text("", encoding="utf-8")
    return module


def test_mod_names_the_module_and_its_python_folder(tmp_path):
    module = _module(tmp_path)
    target = tmp_path / "prefs" / "modules"
    report = module_install.install(target, module)
    text = (target / "meshy_dcc_maya.mod").read_text(encoding="utf-8")
    assert text == "+ meshy_dcc_maya {} {}\nPYTHONPATH+:=python\n".format(__version__, module.as_posix())
    assert report["mod_file"] == str(target / "meshy_dcc_maya.mod")
    assert sorted(p.name for p in target.iterdir()) == ["meshy_dcc_maya.mod"]


def test_reinstall_replaces_and_uninstall_removes(tmp_path):
    module = _module(tmp_path)
    target = tmp_path / "modules"
    module_install.install(target, module)
    module_install.install(target, module)
    assert module_install.uninstall(target)["removed"] is True
    assert module_install.uninstall(target)["removed"] is False
    assert list(target.iterdir()) == []


def test_foreign_mod_file_is_never_replaced_or_removed(tmp_path):
    module = _module(tmp_path)
    target = tmp_path / "modules"
    target.mkdir()
    foreign = target / "meshy_dcc_maya.mod"
    foreign.write_text("+ something_else 1.0 /x\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not written by Meshy DCC"):
        module_install.install(target, module)
    with pytest.raises(RuntimeError, match="not written by Meshy DCC"):
        module_install.uninstall(target)
    assert foreign.read_text(encoding="utf-8") == "+ something_else 1.0 /x\n"


def test_incomplete_module_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="incomplete"):
        module_install.install(tmp_path / "modules", tmp_path / "empty")
    assert not (tmp_path / "modules").exists()


def test_modules_dir_resolution(tmp_path):
    assert module_install.modules_dir({"MESHY_DCC_MAYA_MODULES_DIR": str(tmp_path)}) == tmp_path
    assert module_install.modules_dir({"MAYA_APP_DIR": str(tmp_path)}) == tmp_path / "modules"
    mac = module_install.modules_dir({}, platform="darwin")
    assert mac == Path.home() / "Library" / "Preferences" / "Autodesk" / "maya" / "modules"


def test_cli_runs_isolated_by_path(tmp_path):
    """bin/meshy-dcc-maya runs the file with ``python -I``: no package import, no script dir on sys.path."""
    module = _module(tmp_path)
    script = module / "python" / "meshy_dcc_maya" / "module_install.py"
    script.write_bytes(Path(module_install.__file__).read_bytes())
    target = tmp_path / "modules"
    env = {"MESHY_DCC_MAYA_MODULES_DIR": str(target), "PATH": "/usr/bin:/bin"}
    # The launcher calls it as <package>/bin/../module/python/meshy_dcc_maya/module_install.py.
    via_bin = module.parent / "bin" / ".." / script.relative_to(module.parent)
    (module.parent / "bin").mkdir()
    for action in ("install", "uninstall"):
        done = subprocess.run(
            [sys.executable, "-I", str(via_bin), action, "--json"], capture_output=True, text=True, env=env
        )
        assert done.returncode == 0, done.stderr
        report = json.loads(done.stdout)
        assert report["ok"] is True
        if action == "install":
            assert report["module_dir"] == str(module)
            assert (target / "meshy_dcc_maya.mod").read_text(encoding="utf-8").split()[3] == module.as_posix()
    assert list(target.iterdir()) == []


def test_module_version_matches_the_package():
    assert module_install.MODULE_VERSION == __version__
