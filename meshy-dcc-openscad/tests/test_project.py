"""Project setup for meshy-dcc install / start-instance, and the safe stop."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from meshy_dcc_openscad import project, server

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the fake OpenSCAD is a shell script")


def _fake_openscad(tmp_path: Path, version: str) -> Path:
    executable = tmp_path / "bin" / "openscad"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\necho 'OpenSCAD version %s'\n" % version, encoding="utf-8")
    executable.chmod(0o755)
    return executable


def _install(tmp_path: Path, capsys, version: str) -> "tuple[int, dict, Path]":
    proj = tmp_path / "models"
    proj.mkdir()
    sidecar = tmp_path / "sidecar"
    sidecar.write_text("", encoding="utf-8")
    code = project.install_project(
        [str(proj), "--openscad", str(_fake_openscad(tmp_path, version)), "--sidecar", str(sidecar)]
    )
    return code, json.loads(capsys.readouterr().out), proj


def test_install_records_the_launch_plan(tmp_path, capsys):
    code, report, proj = _install(tmp_path, capsys, "2026.10.15")

    assert code == 0 and report["ok"] is True
    plan = json.loads((proj / ".meshy-dcc" / "launch-plan.json").read_text(encoding="utf-8"))
    assert plan["dcc_type"] == "openscad"
    assert plan["executable"] == str(tmp_path / "sidecar")
    assert plan["argv"][:4] == ["{executable}", "serve", "--project", "{project}"]
    assert plan["argv"][4:] == ["--openscad", report["openscad"]["path"]]
    assert (proj / ".meshy-dcc" / ".gitignore").read_text(encoding="utf-8") == "*\n"


def test_install_refuses_a_host_outside_the_matrix(tmp_path, capsys):
    code, report, proj = _install(tmp_path, capsys, "2019.05")

    assert code == 1 and report["ok"] is False
    assert "2019.05" in report["error"]
    assert not (proj / ".meshy-dcc" / "launch-plan.json").exists()


def test_serve_puts_the_project_first_among_the_roots(tmp_path):
    other = str(tmp_path / "meshy-downloads")
    roots = project._roots(tmp_path, os.pathsep.join([other, str(tmp_path)]))
    assert roots == [str(tmp_path), other]


class _Server:
    instance_id = "abc"

    def __init__(self):
        self._handle = self
        self.metadata = {}

    def update_gateway_metadata(self, metadata):
        self.metadata.update(metadata)


def test_safe_stop_only_for_start_instance_launches(monkeypatch):
    monkeypatch.delenv(server.START_OPERATION_ENV, raising=False)
    fake = _Server()
    server._attach_safe_stop(fake, threading.Event())
    assert fake.metadata == {}


def test_safe_stop_stops_this_instance_only(monkeypatch):
    import meshy_dcc_core.host.safe_stop as safe_stop

    handlers = []
    monkeypatch.setenv(server.START_OPERATION_ENV, "op-1")
    monkeypatch.setattr(safe_stop, "serve_safe_stop", lambda h: handlers.append(h) or "http://x")
    fake, stopped = _Server(), threading.Event()
    server._attach_safe_stop(fake, stopped)

    assert fake.metadata == {"safe_stop_url": "http://x"}
    assert handlers[0]({"instance_id": "other"})[0] == 409 and not stopped.is_set()
    assert handlers[0]({"instance_id": "abc"}) == (202, {"stopping": True})
    assert stopped.wait(5)
