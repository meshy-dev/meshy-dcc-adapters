from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from meshy_dcc_c4d import project as project_module
from meshy_dcc_c4d.project import ProjectError, install_project, uninstall_project
from meshy_dcc_c4d.server import handle_stop_request, main

EXE = "c4dpy.exe" if os.name == "nt" else "c4dpy"


def _c4dpy(tmp_path: Path) -> Path:
    path = tmp_path / "Maxon Cinema 4D 2026" / EXE
    path.parent.mkdir()
    path.write_bytes(b"binary")
    return path


def test_install_records_launch_plan_and_c4dpy(tmp_path: Path) -> None:
    root = tmp_path / "work"
    root.mkdir()
    c4dpy = _c4dpy(tmp_path)

    result = install_project(root, c4dpy, execute=True)

    plan = json.loads((root / ".meshy-dcc" / "launch-plan.json").read_text(encoding="utf-8"))
    config = json.loads((root / ".meshy-dcc" / "c4d.json").read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert plan["dcc_type"] == "c4d"
    assert plan["executable"] == str(Path(sys.executable).absolute())
    assert plan["argv"][0] == "{executable}"
    assert plan["argv"][-3:] == ["serve", "--project", "{project}"]
    assert plan["project_markers"] == [".meshy-dcc/c4d.json"]
    assert config["c4dpy"] == str(c4dpy.resolve())
    assert (root / ".meshy-dcc" / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert project_module.configured_c4dpy(root) == str(c4dpy.resolve())


def test_install_without_yes_writes_nothing(tmp_path: Path) -> None:
    result = install_project(tmp_path, _c4dpy(tmp_path), execute=False)

    assert result["status"] == "planned"
    assert not (tmp_path / ".meshy-dcc").exists()


def test_install_refuses_another_adapters_launch_plan(tmp_path: Path) -> None:
    (tmp_path / ".meshy-dcc").mkdir()
    plan = tmp_path / ".meshy-dcc" / "launch-plan.json"
    plan.write_text('{"dcc_type": "godot"}', encoding="utf-8")

    with pytest.raises(ProjectError) as caught:
        install_project(tmp_path, _c4dpy(tmp_path), execute=True)

    assert caught.value.code == "foreign_launch_plan"
    assert json.loads(plan.read_text(encoding="utf-8")) == {"dcc_type": "godot"}


def test_install_rejects_an_executable_that_is_not_c4dpy(tmp_path: Path) -> None:
    gui = tmp_path / "Cinema 4D"
    gui.write_bytes(b"binary")

    with pytest.raises(ProjectError) as caught:
        install_project(tmp_path, gui, execute=True)

    assert caught.value.code == "c4dpy_invalid"


def test_c4dpy_app_bundle_resolves_to_its_executable(tmp_path: Path) -> None:
    executable = tmp_path / "c4dpy.app" / "Contents" / "MacOS" / "c4dpy"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"binary")

    assert project_module.resolve_c4dpy(tmp_path / "c4dpy.app") == executable.resolve()


def test_uninstall_removes_only_what_install_wrote(tmp_path: Path) -> None:
    install_project(tmp_path, _c4dpy(tmp_path), execute=True)
    document = tmp_path / "scene.c4d"
    document.write_bytes(b"doc")

    result = uninstall_project(tmp_path, execute=True)

    assert sorted(result["files"]) == [".meshy-dcc/c4d.json", ".meshy-dcc/launch-plan.json"]
    assert not (tmp_path / ".meshy-dcc").exists()
    assert document.read_bytes() == b"doc"


def test_uninstall_keeps_a_state_dir_with_other_files(tmp_path: Path) -> None:
    install_project(tmp_path, _c4dpy(tmp_path), execute=True)
    other = tmp_path / ".meshy-dcc" / "other.json"
    other.write_text("{}", encoding="utf-8")

    uninstall_project(tmp_path, execute=True)

    assert other.exists()
    assert not (tmp_path / ".meshy-dcc" / "launch-plan.json").exists()


def test_cli_install_reports_json_and_exit_code(tmp_path: Path, capsys) -> None:
    code = main(["install", "--project", str(tmp_path), "--json", "--yes"])
    failed = json.loads(capsys.readouterr().out)

    assert code == 10
    assert failed["reason"] == "c4dpy_missing"

    code = main(
        ["install", "--project", str(tmp_path), "--c4dpy", str(_c4dpy(tmp_path)), "--json", "--yes"]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_safe_stop_checks_the_instance() -> None:
    stopped = []

    status, body = handle_stop_request({"instance_id": "other"}, "mine", lambda: stopped.append(1))
    assert (status, body["reason"], stopped) == (409, "instance_mismatch", [])

    status, body = handle_stop_request({"instance_id": "mine"}, "mine", lambda: stopped.append(1))
    assert (status, body["stopping"], stopped) == (202, True, [1])


def test_safe_stop_is_advertised_only_for_start_instance(monkeypatch) -> None:
    import threading

    from meshy_dcc_core.host import safe_stop

    from meshy_dcc_c4d import server as server_module

    published = []

    class Handle:
        def update_gateway_metadata(self, metadata):
            published.append(metadata)

    class Server:
        _handle = Handle()
        instance_id = "mine"

    monkeypatch.setattr(safe_stop, "serve_safe_stop", lambda handler: "http://127.0.0.1:1/safe-stop")
    monkeypatch.delenv("MESHY_DCC_START_OPERATION_ID", raising=False)
    server_module._attach_safe_stop(Server(), threading.Event())
    assert published == []

    monkeypatch.setenv("MESHY_DCC_START_OPERATION_ID", "operation")
    server_module._attach_safe_stop(Server(), threading.Event())
    assert published == [{"safe_stop_url": "http://127.0.0.1:1/safe-stop"}]
