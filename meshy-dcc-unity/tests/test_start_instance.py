"""Project setup for `meshy-dcc start-instance` and the consent-gated safe stop."""

import json
from pathlib import Path

import pytest

import meshy_dcc_unity.install as installer
from meshy_dcc_unity._safe_stop import handle_stop_request
from meshy_dcc_unity.install import (
    EXIT_OK,
    EXIT_PREFLIGHT,
    LAUNCH_PLAN_RELATIVE_PATH,
    SIDECAR_CONFIG_RELATIVE_PATH,
)


def make_project(path: Path) -> Path:
    (path / "Assets").mkdir(parents=True)
    (path / "ProjectSettings").mkdir()
    (path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 2021.3.45f1\n", encoding="utf-8"
    )
    return path


def executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_install_records_launch_plan_and_sidecar_then_uninstall_removes_them(tmp_path: Path):
    project = make_project(tmp_path / "project")
    editor = executable(tmp_path / "Unity")
    sidecar = executable(tmp_path / "meshy-dcc-unity-sidecar")
    common = ["--project", str(project), "--json"]

    report, code, _ = installer.run(
        ["install", *common, "--yes", "--files-only", "--dcc-path", str(editor), "--sidecar", str(sidecar)]
    )
    assert code == EXIT_OK, report
    assert report["status"] == "ok"
    assert report["verify"]["readiness"] == {"success": False, "skipped": True}
    plan = json.loads((project / LAUNCH_PLAN_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert plan == {
        "schema_version": 1,
        "dcc_type": "unity",
        "executable": str(editor.resolve()),
        "argv": ["{executable}", "-projectPath", "{project}"],
        "version": "2021.3.45f1",
        "project_markers": ["Assets", "ProjectSettings/ProjectVersion.txt"],
    }
    config = json.loads((project / SIDECAR_CONFIG_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert config["owner"] == "meshy-dcc-unity"
    assert config["environment"] == {"MESHY_DCC_UNITY_SIDECAR_PATH": str(sidecar)}
    assert (project / ".meshy-dcc" / ".gitignore").read_text(encoding="utf-8") == "*\n"

    _, code, _ = installer.run(["uninstall", *common, "--yes"])
    assert code == EXIT_OK
    assert not (project / LAUNCH_PLAN_RELATIVE_PATH).exists()
    assert not (project / SIDECAR_CONFIG_RELATIVE_PATH).exists()


def test_install_with_sidecar_needs_the_project_editor(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("UNITY_EDITOR_PATH", raising=False)
    monkeypatch.setattr(installer, "_resolve_editor", lambda *_args: None)
    project = make_project(tmp_path / "project")
    sidecar = executable(tmp_path / "sidecar")
    report, code, _ = installer.run(
        ["install", "--project", str(project), "--yes", "--json", "--sidecar", str(sidecar)]
    )
    assert code == EXIT_PREFLIGHT
    assert "2021.3.45f1" in json.dumps(report)
    assert not (project / "Packages").exists()
    assert not (project / ".meshy-dcc").exists()


class FakeEditor:
    def __init__(self, dirty: bool, fail: bool = False):
        self.dirty, self.fail, self.calls = dirty, fail, []

    def __call__(self, method, params=None):
        self.calls.append((method, params))
        if self.fail:
            raise RuntimeError("Wait for the Editor to be idle in Edit Mode.")
        if method == "meshy.session":
            return {"host_pid": 42, "workspace": "/p", "dirty": self.dirty}
        return {"quit_requested": True}


@pytest.mark.parametrize(
    ("body", "editor", "status", "reason", "quit_params"),
    [
        ({"instance_id": "other"}, FakeEditor(False), 409, "instance_mismatch", None),
        ({"instance_id": "i"}, FakeEditor(True), 409, "unsaved_changes", None),
        ({"instance_id": "i"}, FakeEditor(True, fail=True), 409, "host_refused", None),
        (
            {"instance_id": "i"},
            FakeEditor(False),
            202,
            None,
            {"expected_pid": 42, "workspace": "/p", "discard_unsaved": False},
        ),
        (
            {"instance_id": "i", "discard_unsaved": True},
            FakeEditor(True),
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
    quits = [params for method, params in editor.calls if method == "meshy.session.quit"]
    assert quits == ([quit_params] if quit_params else [])
