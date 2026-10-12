"""Project install: plugin copy, launch plan, receipt-owned repair, upgrade and uninstall."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meshy_dcc_unreal import install_cli
from meshy_dcc_unreal.__version__ import __version__

PLUGIN = Path("Plugins") / "MeshyDccUnreal"
# The env fixture stubs the engine build; the build-failure test runs the real function on a fake build script.
REAL_BUILD_MODULE = install_cli.build_module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_payload(root: Path, version: str = __version__, body: str = "print('hi')\n") -> Path:
    write_json(root / "MeshyDccUnreal.uplugin", {"VersionName": version, "FriendlyName": "Meshy DCC"})
    (root / "Content" / "Python").mkdir(parents=True)
    (root / "Content" / "Python" / "init_unreal.py").write_text(body, encoding="utf-8")
    (root / "python" / "meshy_dcc_unreal").mkdir(parents=True)
    (root / "python" / "meshy_dcc_unreal" / "__init__.py").write_text("", encoding="utf-8")
    return root


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    engine = tmp_path / "UE_5.7"
    write_json(engine / "Engine" / "Build" / "Build.version", {"MajorVersion": 5, "MinorVersion": 7, "PatchVersion": 2})
    editor = install_cli.editor_executable(engine)
    editor.parent.mkdir(parents=True)
    editor.write_text("", encoding="utf-8")
    payload = make_payload(tmp_path / "payload" / "MeshyDccUnreal")
    project = tmp_path / "Game"
    write_json(project / "Game.uproject", {"FileVersion": 3, "EngineAssociation": "5.7"})
    monkeypatch.setenv(install_cli.ENGINE_ENV, str(engine))
    monkeypatch.setenv(install_cli.PAYLOAD_ENV, str(payload))
    builds = []

    def fake_build(engine_info, project_file, log):
        # What the engine's build tool leaves behind: module binaries and intermediates in the plugin.
        builds.append(project_file)
        plugin = project_file.parent / PLUGIN
        (plugin / "Binaries" / "Mac").mkdir(parents=True, exist_ok=True)
        (plugin / "Binaries" / "Mac" / "UnrealEditor.modules").write_text("{}", encoding="utf-8")
        (plugin / "Intermediate" / "Build").mkdir(parents=True, exist_ok=True)
        log.write_text("built\n", encoding="utf-8")

    monkeypatch.setattr(install_cli, "build_module", fake_build)
    return {"engine": engine, "editor": editor, "payload": payload, "project": project, "builds": builds}


def run(capsys, *argv: str) -> tuple[int, dict]:
    code = install_cli.main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def hidden_work(project: Path) -> list[str]:
    state = project / ".meshy-dcc"
    return sorted(p.name for p in state.iterdir() if p.is_dir() and p.name != "receipts") if state.exists() else []


def test_plan_writes_nothing(env, capsys):
    code, report = run(capsys, "install", str(env["project"]))
    assert code == 0
    assert (report["status"], report["install_mode"]) == ("planned", "fresh")
    assert sorted(p.name for p in env["project"].iterdir()) == ["Game.uproject"]


def test_install_copies_plugin_and_records_launch_plan(env, capsys):
    project = env["project"]
    uproject_before = (project / "Game.uproject").read_bytes()
    code, report = run(capsys, "install", str(project), "--yes")
    assert code == 0, report
    assert (report["status"], report["install_mode"]) == ("ok", "fresh")
    assert (project / PLUGIN / "Content" / "Python" / "init_unreal.py").read_text() == "print('hi')\n"
    assert (project / "Game.uproject").read_bytes() == uproject_before
    plan = json.loads((project / ".meshy-dcc" / "launch-plan.json").read_text())
    assert plan == {
        "schema_version": 1,
        "dcc_type": "unreal",
        "executable": str(env["editor"]),
        "argv": ["{executable}", "{project}/Game.uproject"],
        "version": "5.7.2",
        "project_markers": ["Game.uproject", "Plugins/MeshyDccUnreal/MeshyDccUnreal.uplugin"],
    }
    assert (project / ".meshy-dcc" / ".gitignore").read_text() == "*\n"
    receipt = json.loads((project / ".meshy-dcc" / "receipts" / "unreal.json").read_text())
    assert receipt["adapter_version"] == __version__
    assert set(receipt["files"]) == {
        "MeshyDccUnreal.uplugin",
        "Content/Python/init_unreal.py",
        "python/meshy_dcc_unreal/__init__.py",
    }

    assert env["builds"] == [project / "Game.uproject"]
    assert (project / ".meshy-dcc" / "build.log").read_text() == "built\n"

    # Build output and Python caches do not count as foreign files, and a built module is not rebuilt.
    cache = project / PLUGIN / "Content" / "Python" / "__pycache__"
    cache.mkdir()
    (cache / "init_unreal.cpython-311.pyc").write_bytes(b"\0")
    code, report = run(capsys, "install", str(project), "--yes")
    assert (code, report["install_mode"]) == (0, "current")
    assert len(env["builds"]) == 1
    assert hidden_work(project) == []


def test_upgrade_replaces_the_plugin_and_removes_the_old_copy(env, capsys, monkeypatch, tmp_path):
    project = env["project"]
    assert run(capsys, "install", str(project), "--yes")[0] == 0
    (project / PLUGIN / "python" / "__pycache__").mkdir()
    newer = make_payload(tmp_path / "newer" / "MeshyDccUnreal", version="9.9.9", body="print('new')\n")
    monkeypatch.setenv(install_cli.PAYLOAD_ENV, str(newer))
    monkeypatch.setattr(install_cli, "__version__", "9.9.9")

    code, report = run(capsys, "install", str(project), "--yes")
    assert code == 0, report
    assert report["install_mode"] == "upgrade"
    assert (project / PLUGIN / "Content" / "Python" / "init_unreal.py").read_text() == "print('new')\n"
    assert not (project / PLUGIN / "python" / "__pycache__").exists()
    assert hidden_work(project) == []


def test_repair_restores_a_deleted_file(env, capsys):
    project = env["project"]
    run(capsys, "install", str(project), "--yes")
    (project / PLUGIN / "Content" / "Python" / "init_unreal.py").unlink()
    assert run(capsys, "status", str(project))[1]["status"] == "incomplete"
    code, report = run(capsys, "install", str(project), "--yes")
    assert (code, report["install_mode"]) == (0, "repair")
    assert (project / PLUGIN / "Content" / "Python" / "init_unreal.py").is_file()


@pytest.mark.parametrize("change", ["added", "edited"])
def test_foreign_or_edited_files_block_install_and_uninstall(env, capsys, change):
    project = env["project"]
    run(capsys, "install", str(project), "--yes")
    if change == "added":
        target = project / PLUGIN / "Content" / "Python" / "my_tool.py"
    else:
        target = project / PLUGIN / "Content" / "Python" / "init_unreal.py"
    target.write_text("user work\n", encoding="utf-8")
    receipt = (project / ".meshy-dcc" / "receipts" / "unreal.json").read_bytes()

    for verb in ("install", "uninstall"):
        code, report = run(capsys, verb, str(project), "--yes")
        assert code == install_cli.EXIT_PREFLIGHT, report
        assert report["files"] == [target.relative_to(project / PLUGIN).as_posix()]
    assert target.read_text() == "user work\n"
    assert (project / ".meshy-dcc" / "receipts" / "unreal.json").read_bytes() == receipt
    assert run(capsys, "status", str(project))[1]["status"] == "modified"


def test_a_plugin_folder_without_receipt_is_left_alone(env, capsys):
    project = env["project"]
    (project / PLUGIN).mkdir(parents=True)
    (project / PLUGIN / "notes.txt").write_text("mine", encoding="utf-8")
    for verb in ("install", "uninstall"):
        assert run(capsys, verb, str(project), "--yes")[0] == install_cli.EXIT_PREFLIGHT
    assert (project / PLUGIN / "notes.txt").read_text() == "mine"
    assert run(capsys, "status", str(project))[1]["status"] == "unowned"


def test_failed_install_rolls_back_to_the_previous_plugin(env, capsys, monkeypatch, tmp_path):
    project = env["project"]
    run(capsys, "install", str(project), "--yes")
    before = {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    newer = make_payload(tmp_path / "newer" / "MeshyDccUnreal", version="9.9.9", body="print('new')\n")
    monkeypatch.setenv(install_cli.PAYLOAD_ENV, str(newer))
    monkeypatch.setattr(install_cli, "__version__", "9.9.9")
    real = install_cli._write_json

    def fail_on_receipt(path, value):
        if path.name == "unreal.json":
            raise OSError("disk full")
        real(path, value)

    monkeypatch.setattr(install_cli, "_write_json", fail_on_receipt)
    code, report = run(capsys, "install", str(project), "--yes")
    assert code == install_cli.EXIT_INSTALL, report
    after = {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    assert after == before


def test_a_failed_build_rolls_back_to_the_previous_plugin(env, capsys, monkeypatch, tmp_path):
    project = env["project"]
    run(capsys, "install", str(project), "--yes")
    before = {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    newer = make_payload(tmp_path / "newer" / "MeshyDccUnreal", version="9.9.9", body="print('new')\n")
    monkeypatch.setenv(install_cli.PAYLOAD_ENV, str(newer))
    monkeypatch.setattr(install_cli, "__version__", "9.9.9")
    script = tmp_path / "Build.sh"
    script.write_text("#!/bin/sh\necho 'ERROR: Platform Mac is not a valid platform to build.'\nexit 6\n")
    script.chmod(0o755)
    monkeypatch.setattr(install_cli, "build_command", lambda *_args: [str(script)])
    monkeypatch.setattr(install_cli, "build_module", REAL_BUILD_MODULE)

    code, report = run(capsys, "install", str(project), "--yes")
    assert code == install_cli.EXIT_BUILD, report
    assert "not a valid platform" in report["log_tail"][-1]
    after = {
        p.relative_to(project).as_posix(): p.read_bytes()
        for p in project.rglob("*")
        if p.is_file() and p.name != "build.log"
    }
    assert after == {name: data for name, data in before.items() if not name.endswith("build.log")}


def test_uninstall_removes_only_what_install_wrote(env, capsys):
    project = env["project"]
    (project / "Plugins" / "Other").mkdir(parents=True)
    run(capsys, "install", str(project), "--yes")
    (project / PLUGIN / "Content" / "Python" / "__pycache__").mkdir()
    code, report = run(capsys, "uninstall", str(project), "--yes")
    assert (code, report["status"]) == (0, "removed")
    assert not (project / PLUGIN).exists()
    assert not (project / ".meshy-dcc").exists()
    assert (project / "Plugins" / "Other").is_dir()
    assert run(capsys, "uninstall", str(project), "--yes")[1]["status"] == "absent"


def test_engine_must_match_the_project(env, capsys):
    write_json(env["project"] / "Game.uproject", {"EngineAssociation": "5.6"})
    code, report = run(capsys, "install", str(env["project"]), "--yes")
    assert code == install_cli.EXIT_PREFLIGHT
    assert "5.6" in report["message"]


def test_engine_is_found_through_the_launcher(env, capsys, monkeypatch):
    monkeypatch.delenv(install_cli.ENGINE_ENV)
    monkeypatch.setattr(install_cli, "_launcher_installs", lambda: {"UE_5.7": env["engine"]})
    code, report = run(capsys, "install", str(env["project"]))
    assert code == 0, report
    assert report["engine"]["root"] == str(env["engine"])


def test_a_project_that_disables_python_is_refused(env, capsys):
    write_json(
        env["project"] / "Game.uproject",
        {"EngineAssociation": "5.7", "Plugins": [{"Name": "PythonScriptPlugin", "Enabled": False}]},
    )
    code, report = run(capsys, "install", str(env["project"]), "--yes")
    assert code == install_cli.EXIT_PREFLIGHT
    assert "PythonScriptPlugin" in report["message"]
    assert not (env["project"] / "Plugins").exists()


def test_windows_build_runs_build_bat_directly(monkeypatch, tmp_path):
    # `cmd /c "<Program Files>\...\Build.bat" ... "-Project=<path with spaces>"` loses
    # its first and last quotes; the batch file is run directly instead.
    monkeypatch.setattr(install_cli.sys, "platform", "win32")
    project = tmp_path / "Unreal Projects" / "My Game.uproject"
    command = install_cli.build_command(tmp_path / "Program Files" / "UE_5.7", project)
    assert command[0].endswith("Build.bat")
    assert "cmd" not in command[0].lower().split("/")[-1]
    assert command[1:3] == ["Development", "Win64"]
    assert f"-Project={project}" in command
