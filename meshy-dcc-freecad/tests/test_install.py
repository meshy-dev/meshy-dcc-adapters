"""Project setup for meshy-dcc start-instance, and the safe stop it advertises."""

import json
import os
import stat
from pathlib import Path

import pytest

from meshy_dcc_freecad import bridge, install, server


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.mark.parametrize(
    "given, command",
    [
        ("FreeCAD.app/Contents/MacOS/FreeCAD", "FreeCAD.app/Contents/Resources/bin/freecadcmd"),
        ("FreeCAD.app", "FreeCAD.app/Contents/Resources/bin/freecadcmd"),
        ("FreeCAD 1.1/bin/FreeCAD.exe", "FreeCAD 1.1/bin/FreeCADCmd.exe"),
        ("bin/freecadcmd", "bin/freecadcmd"),
    ],
)
def test_freecadcmd_is_found_from_what_the_operator_names(tmp_path, given, command):
    expected = _executable(tmp_path / command)
    if not (tmp_path / given).exists():
        _executable(tmp_path / given)
    assert install.freecadcmd(tmp_path / given).samefile(expected)


def _verified(monkeypatch):
    report = {
        "_exit_code": 0,
        "checks": {"runtime": {"freecad_version": "1.1.4"}},
        "verify": {"failure_reason": None},
    }
    monkeypatch.setattr("meshy_dcc_freecad.doctor.doctor_report", lambda *args: dict(report))


def test_install_writes_a_launch_plan_and_uninstall_removes_it(tmp_path, monkeypatch):
    _verified(monkeypatch)
    monkeypatch.delenv(install.ROOTS_ENV, raising=False)
    command = _executable(tmp_path / "bin" / "freecadcmd")
    project = tmp_path / "project"
    project.mkdir()

    report, code = install.install(project, command, 30)

    assert code == 0 and report["freecad_version"] == "1.1.4"
    plan = json.loads((project / install.PLAN).read_text())
    assert plan["dcc_type"] == "freecad" and plan["version"] == "1.1.4"
    assert plan["argv"][:4] == ["{executable}", "-I", "-m", "meshy_dcc_freecad"]
    assert plan["argv"][plan["argv"].index("--project") + 1] == "{project}"
    assert plan["argv"][plan["argv"].index("--freecad") + 1] == str(command)
    assert (project / ".meshy-dcc" / ".gitignore").read_text() == "*\n"

    report, code = install.uninstall(project)
    assert code == 0 and not (project / ".meshy-dcc").exists()


def test_install_leaves_another_adapters_plan_alone(tmp_path, monkeypatch):
    _verified(monkeypatch)
    project = tmp_path / "project"
    (project / ".meshy-dcc").mkdir(parents=True)
    (project / install.PLAN).write_text(json.dumps({"dcc_type": "godot"}))

    report, code = install.install(project, _executable(tmp_path / "freecadcmd"), 30)

    assert code == 10 and "another adapter" in report["reason"]
    assert json.loads((project / install.PLAN).read_text()) == {"dcc_type": "godot"}
    assert install.uninstall(project)[0]["removed"] == []


@pytest.fixture
def run_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(bridge.RUN_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(server, "_stop_when_idle", lambda: None)
    return tmp_path


def test_a_running_call_refuses_a_stop_unless_discarded(run_dir):
    (run_dir / str(os.getpid())).touch()  # a live process standing in for FreeCADCmd

    status, reply = server.handle_stop_request({"instance_id": "abc"}, "abc")
    assert (status, reply["reason"]) == (409, "call_in_progress")
    assert not (run_dir / bridge.STOPPING_MARKER).exists()

    status, reply = server.handle_stop_request(
        {"instance_id": "abc", "discard_unsaved": True}, "abc"
    )
    assert (status, reply["cancelled_calls"]) == (202, 1)
    assert (run_dir / bridge.STOPPING_MARKER).exists()


def test_an_idle_service_stops_and_refuses_new_calls(run_dir):
    (run_dir / "99999999").touch()  # a finished call's marker is pruned, not counted
    assert server.handle_stop_request({"instance_id": "abc"}, "abc") == (
        202,
        {"stopping": True, "cancelled_calls": 0},
    )
    assert not (run_dir / "99999999").exists()
    with pytest.raises(bridge.BridgeError) as error:
        bridge._spawn(["true"])
    assert error.value.code == "service_stopping"


def test_a_stop_for_another_instance_is_refused(run_dir):
    assert server.handle_stop_request({"instance_id": "other"}, "abc")[0] == 409
