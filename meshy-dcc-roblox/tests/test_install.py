import json
import sys
from pathlib import Path

import pytest

from meshy_dcc_roblox import cli, install


@pytest.fixture
def plugins(tmp_path, monkeypatch):
    folder = tmp_path / "Plugins"
    monkeypatch.setenv("MESHY_DCC_ROBLOX_PLUGINS_DIR", str(folder))
    return folder


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "Castle.rbxl").write_bytes(b"place")
    return root


def test_install_writes_plugin_binding_and_launch_plan(plugins, project):
    report = install.install(project)
    plugin = plugins / "MeshyDcc.lua"
    assert report["place_file"] == "Castle.rbxl" and report["plugin"] == str(plugin)
    assert plugin.read_text(encoding="utf-8") == install.PLUGIN_SOURCE.read_text(encoding="utf-8")
    config = json.loads((project / ".meshy-dcc" / "roblox.json").read_text())
    assert config["place_file"] == "Castle.rbxl" and config["version"] == "0.1.0"
    plan = json.loads((project / ".meshy-dcc" / "launch-plan.json").read_text())
    assert plan["dcc_type"] == "roblox"
    assert plan["executable"] == str(Path(sys.executable).absolute())
    assert plan["argv"] == ["{executable}", "-I", "-m", "meshy_dcc_roblox", "launch", "--project", "{project}"]
    assert plan["project_markers"] == [".meshy-dcc/roblox.json", "Castle.rbxl"]
    assert (project / ".meshy-dcc" / ".gitignore").read_text() == "*\n"
    assert install.status(project)["plugin_current"] is True
    install.install(project)  # again: same result, no error
    assert install.status(project)["project"]["place_file"] == "Castle.rbxl"


def test_install_binds_a_published_place(plugins, tmp_path):
    report = install.install(tmp_path, place_id=74265016723074, universe_id=7127583708)
    assert report["place_id"] == 74265016723074
    plan = json.loads((tmp_path / ".meshy-dcc" / "launch-plan.json").read_text())
    assert plan["project_markers"] == [".meshy-dcc/roblox.json"]
    with pytest.raises(install.InstallError, match="go together"):
        install.install(tmp_path, place_id=1)


def test_install_needs_exactly_one_place_inside_the_project(plugins, project):
    (project / "Other.rbxlx").write_text("<roblox/>")
    with pytest.raises(install.InstallError, match="2 place files"):
        install.install(project)
    assert install.install(project, place="Other.rbxlx")["place_file"] == "Other.rbxlx"
    for outside in ("../Castle.rbxl", "missing.rbxl", "notes.txt"):
        with pytest.raises(install.InstallError, match="directly inside"):
            install.install(project, place=outside)


def test_a_foreign_plugin_file_is_left_alone(plugins, project):
    plugins.mkdir()
    (plugins / "MeshyDcc.lua").write_text("print('mine')\n")
    with pytest.raises(install.InstallError, match="not the Meshy DCC plugin"):
        install.install(project)
    assert install.uninstall(project, plugin=True)["removed"] == []
    assert (plugins / "MeshyDcc.lua").read_text() == "print('mine')\n"


def test_uninstall_removes_only_what_install_wrote(plugins, project):
    install.install(project)
    (project / ".meshy-dcc" / "notes.txt").write_text("user file")
    removed = install.uninstall(project, plugin=True)["removed"]
    assert len(removed) == 4
    assert not (plugins / "MeshyDcc.lua").exists()
    assert sorted(p.name for p in (project / ".meshy-dcc").iterdir()) == ["notes.txt"]
    assert (project / "Castle.rbxl").read_bytes() == b"place"


def test_studio_command_opens_the_bound_place(plugins, project, monkeypatch, tmp_path):
    studio = tmp_path / "RobloxStudio"
    studio.write_text("")
    monkeypatch.setenv(cli.STUDIO_ENV, str(studio))
    install.install(project)
    argv, expect = cli.studio_command(project)
    assert argv == [str(studio), "--task", "EditFile", "--localPlaceFile", str(project / "Castle.rbxl")]
    assert expect == {"place_file": "Castle.rbxl"}
    install.install(project, place_id=5, universe_id=6)
    argv, expect = cli.studio_command(project)
    assert argv[1:] == ["--task", "EditPlace", "--placeId", "5", "--universeId", "6"]
    assert expect == {"place_id": 5}


def test_cli_reports_errors_as_json(plugins, tmp_path, capsys):
    assert cli.main(["install", "--project", str(tmp_path / "missing")]) == 1
    assert "existing directory" in json.loads(capsys.readouterr().out)["error"]
