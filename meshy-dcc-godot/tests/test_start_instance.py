"""Project setup for `meshy-dcc start-instance` and the consent-gated safe stop."""

import json
from pathlib import Path

import pytest

from meshy_dcc_godot import install as install_module
from meshy_dcc_godot._safe_stop import handle_stop_request
from meshy_dcc_godot.install import (
    INSTALL_EXIT_OK,
    INSTALL_EXIT_PREFLIGHT,
    LAUNCH_PLAN_RELATIVE_PATH,
    SIDECAR_CONFIG_RELATIVE_PATH,
    main,
)


def executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "project.godot").write_text("[application]\n", encoding="utf-8")
    godot = executable(tmp_path / "Godot")
    monkeypatch.setattr(
        install_module,
        "_probe_godot",
        lambda _path: {"path": str(godot), "version": "4.7.2.stable", "version_tuple": (4, 7, 2)},
    )
    monkeypatch.setenv("MESHY_DCC_GODOT_EXECUTABLE", str(godot))
    return root


def run(capsys, *argv: str) -> tuple[int, dict]:
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_files_only_install_records_launch_plan_then_uninstall_removes_it(
    project: Path, tmp_path: Path, capsys, monkeypatch
):
    sidecar = executable(tmp_path / "meshy-dcc-godot-sidecar")
    install = ["install", str(project), "--yes", "--json", "--files-only", "--sidecar", str(sidecar)]

    code, report = run(capsys, *install)
    assert code == INSTALL_EXIT_OK, report
    assert report["status"] == "ok"
    assert report["verify"]["readiness"] == {"success": False, "skipped": True}
    plan = json.loads((project / LAUNCH_PLAN_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert plan == {
        "schema_version": 1,
        "dcc_type": "godot",
        "executable": str(tmp_path / "Godot"),
        "argv": ["{executable}", "--editor", "--path", "{project}"],
        "version": "4.7.2.stable",
        "project_markers": ["project.godot"],
    }
    config = json.loads((project / SIDECAR_CONFIG_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert config["owner"] == "meshy-dcc-godot"
    assert config["sidecar"] == str(sidecar)
    assert (project / ".meshy-dcc" / ".gitignore").read_text(encoding="utf-8") == "*\n"

    # The same version again leaves the addon alone instead of parking a backup.
    code, report = run(capsys, *install)
    assert code == INSTALL_EXIT_OK, report
    assert report["install_mode"] == "current"
    assert not list((project / "addons").glob(".meshy_dcc_godot.*"))

    # A newer adapter over this one replaces the addon and removes the old copy.
    monkeypatch.setattr(install_module, "__version__", "0.1.1")
    code, report = run(capsys, *install)
    assert code == INSTALL_EXIT_OK, report
    assert report["install_mode"] == "repair"
    assert not list((project / "addons").glob(".meshy_dcc_godot.*"))

    code, _ = run(capsys, "uninstall", str(project), "--yes", "--json")
    assert code == INSTALL_EXIT_OK
    assert not (project / LAUNCH_PLAN_RELATIVE_PATH).exists()
    assert not (project / SIDECAR_CONFIG_RELATIVE_PATH).exists()


def test_missing_sidecar_fails_preflight_without_writing(project: Path, tmp_path: Path, capsys):
    code, report = run(
        capsys, "install", str(project), "--yes", "--json", "--sidecar", str(tmp_path / "absent")
    )
    assert code == INSTALL_EXIT_PREFLIGHT, report
    assert not (project / "addons").exists()
    assert not (project / ".meshy-dcc").exists()


class FakeEditor:
    def __init__(self, dirty, fail: bool = False):
        self.dirty, self.fail, self.calls = dirty, fail, []

    def __call__(self, method, params=None):
        self.calls.append((method, params))
        if self.fail:
            raise RuntimeError("Refusing to quit a different Godot project")
        if method == "meshy.session":
            return {"host_pid": 42, "workspace": "/p", "dirty": self.dirty}
        return {"quit_requested": True}


@pytest.mark.parametrize(
    ("body", "editor", "status", "reason", "quit_params"),
    [
        ({"instance_id": "other"}, FakeEditor(False), 409, "instance_mismatch", None),
        ({"instance_id": "i"}, FakeEditor(True), 409, "unsaved_changes", None),
        # An editor that cannot report unsaved state counts as unsaved.
        ({"instance_id": "i"}, FakeEditor(None), 409, "unsaved_changes", None),
        ({"instance_id": "i"}, FakeEditor(False, fail=True), 409, "host_refused", None),
        (
            {"instance_id": "i"},
            FakeEditor(False),
            202,
            None,
            {"expected_pid": 42, "workspace": "/p", "discard_unsaved": False},
        ),
        (
            {"instance_id": "i", "discard_unsaved": True},
            FakeEditor(None),
            202,
            None,
            {"expected_pid": 42, "workspace": "/p", "discard_unsaved": True},
        ),
    ],
)
def test_safe_stop_quits_only_saved_or_consented_editors(body, editor, status, reason, quit_params):
    code, reply = handle_stop_request(body, "i", editor)
    assert code == status
    assert reply.get("reason") == reason
    quits = [params for method, params in editor.calls if method == "meshy.quit"]
    assert quits == ([quit_params] if quit_params else [])
