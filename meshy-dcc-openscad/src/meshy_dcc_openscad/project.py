"""One OpenSCAD workspace per project, for ``meshy-dcc install`` and ``start-instance``.

OpenSCAD has nothing to install into: the adapter drives its CLI. A project
is a directory of ``.scad`` sources and outputs. ``install-project`` checks the
OpenSCAD executable and records the project's start-instance launch plan;
``serve`` runs the adapter with that project as its workspace root.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .bridge import OpenscadCli
from .compat import SUPPORTED, unsupported_reason

LAUNCH_PLAN = Path(".meshy-dcc") / "launch-plan.json"
EXECUTABLE_ENV = "MESHY_DCC_OPENSCAD_EXECUTABLE"
ROOTS_ENV = "MESHY_DCC_OPENSCAD_ALLOWED_ROOTS"


def install_project(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-openscad install-project")
    parser.add_argument("project", type=Path)
    parser.add_argument("--openscad", type=Path, required=True, help="OpenSCAD executable")
    parser.add_argument("--sidecar", type=Path, required=True, help="Launcher start-instance runs")
    args = parser.parse_args(argv)
    project = args.project.absolute()
    sidecar = args.sidecar.absolute()
    report = {"ok": False, "project": str(project)}
    try:
        if not project.is_dir():
            raise ValueError("project is not a directory: %s" % project)
        if not sidecar.is_file():
            raise ValueError("sidecar not found: %s" % sidecar)
        cli = OpenscadCli(str(args.openscad.absolute()), allowed_roots=[project])
        if cli.executable is None:
            raise ValueError("OpenSCAD executable not found: %s" % args.openscad)
        status = cli.status()
        verdict = status["host_matrix"]
        report["openscad"] = {"path": cli.executable, "version": status.get("version")}
        if not status["ready"]:
            raise ValueError("OpenSCAD did not answer --version: %s" % cli.executable)
        if verdict["status"] != SUPPORTED:
            raise ValueError(unsupported_reason(verdict))
        plan = {
            "schema_version": 1,
            "dcc_type": "openscad",
            "executable": str(sidecar),
            "argv": [
                "{executable}",
                "serve",
                "--project",
                "{project}",
                "--openscad",
                cli.executable,
            ],
        }
        folder = project / LAUNCH_PLAN.parent
        folder.mkdir(exist_ok=True)
        (folder / ".gitignore").write_text("*\n", encoding="utf-8")
        staged = folder / (LAUNCH_PLAN.name + ".tmp")
        staged.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        os.replace(str(staged), str(project / LAUNCH_PLAN))
        report.update(ok=True, launch_plan=str(project / LAUNCH_PLAN))
    except (OSError, ValueError) as exc:
        report["error"] = str(exc)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


def serve(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-openscad serve")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args(argv)
    project = args.project.absolute()
    if not project.is_dir():
        print("project is not a directory: %s" % project, file=sys.stderr)
        return 1
    os.environ[EXECUTABLE_ENV] = str(args.openscad)
    os.environ[ROOTS_ENV] = os.pathsep.join(_roots(project, os.environ.get(ROOTS_ENV)))
    # Workspace-relative tool paths resolve against the project.
    os.chdir(str(project))
    from .server import _run_server

    _run_server()
    return 0


def _roots(project: Path, extra: Optional[str]) -> List[str]:
    """The project first, then any roots the operator already configured."""
    roots = [str(project)]
    for item in (extra or "").split(os.pathsep):
        if item.strip() and item.strip() not in roots:
            roots.append(item.strip())
    return roots
