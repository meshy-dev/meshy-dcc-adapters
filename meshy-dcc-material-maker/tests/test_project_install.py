from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from meshy_dcc_core.deployment import load_install_sop_schema

from meshy_dcc_material_maker import cli, server


@pytest.fixture
def setup(tmp_path):
    install = tmp_path / "Material Maker.app" / "Contents" / "MacOS"
    (install / "nodes").mkdir(parents=True)
    (install / "nodes" / "material.mmg").write_text("{}", encoding="utf-8")
    (install / "Material Maker").write_bytes(b"fixture")
    sidecar = tmp_path / "bin" / "meshy-dcc-material-maker-sidecar"
    sidecar.parent.mkdir()
    sidecar.write_text("#!/bin/sh\n", encoding="utf-8")
    project = tmp_path / "materials"
    project.mkdir()
    return tmp_path / "Material Maker.app", sidecar, project


def run(argv, capsys):
    code = cli.main(argv + ["--json"])
    report = json.loads(capsys.readouterr().out)
    Draft202012Validator(load_install_sop_schema()).validate(report)
    return code, report


def test_install_writes_launch_plan_config_and_receipt(setup, capsys):
    app, sidecar, project = setup
    argv = ["install-project", str(project), "--dcc-path", str(app), "--sidecar", str(sidecar)]
    code, plan = run(argv, capsys)
    assert code == 0 and plan["status"] == "planned"
    assert not (project / ".meshy-dcc").exists()

    code, report = run(argv + ["--yes"], capsys)
    assert code == 0 and report["status"] == "ok"
    state = project / ".meshy-dcc"
    launch = json.loads((state / "launch-plan.json").read_text())
    assert launch["dcc_type"] == "material-maker"
    assert launch["executable"] == str(sidecar)
    assert launch["argv"] == ["{executable}", "serve", "--project", "{project}"]
    config = json.loads((state / "material-maker.json").read_text())
    assert config["executable"] == str((app / "Contents" / "MacOS" / "Material Maker").resolve())
    assert (state / ".gitignore").read_text() == "*\n"
    receipt = json.loads((state / "receipts" / "material-maker.json").read_text())
    assert {f["path"] for f in receipt["owned_files"]} == {"launch-plan.json", "material-maker.json", ".gitignore"}

    code, again = run(argv + ["--yes"], capsys)
    assert code == 0 and {s["status"] for s in again["steps"]} == {"current"}

    # The server reads the recorded executable for its tools.
    assert server.read_project_config(project.resolve())["executable"] == config["executable"]

    code, removed = run(["uninstall-project", str(project), "--yes"], capsys)
    assert code == 0 and {s["status"] for s in removed["steps"]} == {"removed"}
    assert not state.exists()


def test_install_never_takes_over_another_adapters_folder(setup, capsys):
    app, sidecar, project = setup
    state = project / ".meshy-dcc"
    state.mkdir()
    (state / "launch-plan.json").write_text('{"dcc_type": "godot"}', encoding="utf-8")
    (state / ".gitignore").write_text("receipts/\n", encoding="utf-8")
    argv = ["install-project", str(project), "--dcc-path", str(app), "--sidecar", str(sidecar), "--yes"]
    code, report = run(argv, capsys)
    assert code == 30 and report["verify"]["failure_reason"] == "file_not_owned"
    assert (state / "launch-plan.json").read_text() == '{"dcc_type": "godot"}'


def test_uninstall_keeps_files_changed_after_install(setup, capsys):
    app, sidecar, project = setup
    run(["install-project", str(project), "--dcc-path", str(app), "--sidecar", str(sidecar), "--yes"], capsys)
    config = project / ".meshy-dcc" / "material-maker.json"
    config.write_text("{}", encoding="utf-8")
    code, report = run(["uninstall-project", str(project), "--yes"], capsys)
    assert code == 0
    assert {s["id"]: s["status"] for s in report["steps"]}["material-maker.json"] == "kept"
    assert config.read_text() == "{}"


@pytest.mark.parametrize("problem", ["not_material_maker", "relative_project", "missing_sidecar"])
def test_install_fails_closed(setup, tmp_path, capsys, problem):
    app, sidecar, project = setup
    if problem == "not_material_maker":
        other = tmp_path / "other"
        other.write_bytes(b"x")
        app = other
    argv = [
        "install-project",
        "materials" if problem == "relative_project" else str(project),
        "--dcc-path",
        str(app),
        "--sidecar",
        str(tmp_path / "missing") if problem == "missing_sidecar" else str(sidecar),
        "--yes",
    ]
    code, report = run(argv, capsys)
    assert code == 30 and report["status"] == "failed"
    assert not (project / ".meshy-dcc").exists()


def test_server_binds_to_the_project_and_its_recorded_material_maker(setup, monkeypatch, capsys):
    app, sidecar, project = setup
    run(["install-project", str(project), "--dcc-path", str(app), "--sidecar", str(sidecar), "--yes"], capsys)
    monkeypatch.delenv("MESHY_DCC_MATERIAL_MAKER_EXECUTABLE", raising=False)
    monkeypatch.setenv("MESHY_DCC_START_PROJECT", str(project))
    monkeypatch.setenv("MESHY_DCC_MATERIAL_MAKER_PROJECT", "")
    root = server.configure_project(None)
    assert root == project.resolve()
    from meshy_dcc_material_maker.bridge import MaterialMakerCli

    bound = MaterialMakerCli.from_env()
    assert bound.project_root == project.resolve()
    assert Path(bound.executable).name == "Material Maker"


def test_safe_stop_accepts_only_its_own_instance():
    assert server.handle_stop_request({"instance_id": "other"}, "mine")[0] == 409
    assert server.handle_stop_request({"instance_id": "mine"}, "mine") == (202, {"stopping": True})
    assert server._stopped.wait(5)
    server._stopped.clear()
