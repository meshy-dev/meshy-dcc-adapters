"""Set a project directory up for ``meshy-dcc start-instance``.

``install`` finds FreeCADCmd from the FreeCAD the operator named, proves it
with the doctor (a real FreeCADCmd run checked against the compatibility
matrix), then writes ``<project>/.meshy-dcc/launch-plan.json``: start-instance
runs this package's Python with ``serve`` for that project. The plan holds
machine-local paths, so ``.meshy-dcc/`` ignores itself for version control.
``uninstall`` removes the plan again. Nothing is written into FreeCAD or the
user's FreeCAD settings.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from .__version__ import __version__
from .bridge import FreecadBridge

PLAN = Path(".meshy-dcc") / "launch-plan.json"
ROOTS_ENV = "MESHY_DCC_FREECAD_ALLOWED_ROOTS"
EXECUTABLE_ENV = "MESHY_DCC_FREECAD_EXECUTABLE"


def freecadcmd(dcc_path: Path) -> Optional[Path]:
    """FreeCADCmd for a FreeCAD app bundle, ``FreeCAD.exe``/``FreeCAD`` or FreeCADCmd itself."""
    path = Path(dcc_path).expanduser().absolute()
    if path.is_file() and path.name.lower().startswith("freecadcmd"):
        return path
    # bin/FreeCAD.exe -> bin/FreeCADCmd.exe; FreeCAD.app/Contents/MacOS/FreeCAD -> FreeCAD.app
    for base in (path, *list(path.parents)[:3]):
        if base.is_dir():
            found = FreecadBridge._resolve_executable(str(base))
            if found:
                return Path(found)
    return None


def service_python() -> str:
    """This interpreter; on Windows its windowless twin, so the service opens no console."""
    python = os.path.abspath(sys.executable)
    windowless = os.path.join(os.path.dirname(python), "pythonw.exe")
    return windowless if os.name == "nt" and os.path.isfile(windowless) else python


def launch_plan(project: Path, command: Path, version: str) -> dict[str, Any]:
    """Run the service isolated (-I: no current directory on sys.path) for ``{project}``."""
    return {
        "schema_version": 1,
        "dcc_type": "freecad",
        "executable": service_python(),
        "argv": [
            "{executable}",
            "-I",
            "-m",
            "meshy_dcc_freecad",
            "serve",
            "--project",
            "{project}",
            "--freecad",
            str(command),
            "--freecad-version",
            version,
        ],
        "version": version,
        "project_markers": [],
    }


def _existing_plan(project: Path) -> Optional[dict]:
    try:
        return json.loads((project / PLAN).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def install(project: Path, dcc_path: Optional[Path], timeout: float) -> tuple[dict, int]:
    from .doctor import doctor_report

    report: dict[str, Any] = {
        "schema_version": 1,
        "dcc_type": "freecad",
        "verb": "install",
        "adapter_version": __version__,
        "project": str(project),
    }
    if not project.is_dir():
        return {**report, "status": "failed", "reason": "project is not a directory"}, 10
    plan = _existing_plan(project)
    if (project / PLAN).exists() and (plan is None or plan.get("dcc_type") != "freecad"):
        return {
            **report,
            "status": "failed",
            "reason": "%s belongs to another adapter; use another project directory" % PLAN,
        }, 10
    if dcc_path:
        command = freecadcmd(dcc_path)
        if command is None:
            return {**report, "status": "failed", "reason": "no FreeCADCmd for %s" % dcc_path}, 10
    else:
        found = FreecadBridge._resolve_executable(os.environ.get(EXECUTABLE_ENV))
        command = Path(found) if found else None
    # The service's documents live in the project, so the doctor checks that root.
    os.environ.setdefault(ROOTS_ENV, str(project))
    doctor = doctor_report(command, "verify", timeout)
    exit_code = int(doctor.pop("_exit_code"))
    report["doctor"] = doctor
    if exit_code != 0:
        return {
            **report,
            "status": "failed",
            "reason": doctor["verify"]["failure_reason"],
        }, exit_code
    runtime = doctor["checks"]["runtime"]
    state = project / PLAN.parent
    state.mkdir(exist_ok=True)
    if not (state / ".gitignore").exists():
        (state / ".gitignore").write_text("*\n", encoding="utf-8")
    plan = launch_plan(project, command, runtime["freecad_version"])
    staged = state / "launch-plan.json.tmp"
    staged.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    os.replace(staged, project / PLAN)
    report.update(
        status="ok",
        launch_plan=str(project / PLAN),
        freecad_executable=str(command),
        freecad_version=runtime["freecad_version"],
    )
    return report, 0


def uninstall(project: Path) -> tuple[dict, int]:
    report = {
        "schema_version": 1,
        "dcc_type": "freecad",
        "verb": "uninstall",
        "project": str(project),
    }
    plan = _existing_plan(project)
    if plan is None or plan.get("dcc_type") != "freecad":
        return {**report, "status": "ok", "removed": []}, 0
    removed = [project / PLAN]
    (project / PLAN).unlink()
    state = project / PLAN.parent
    ignore = state / ".gitignore"
    if [entry.name for entry in state.iterdir()] == [".gitignore"] and ignore.read_text() == "*\n":
        ignore.unlink()
        state.rmdir()
        removed.append(state)
    return {**report, "status": "ok", "removed": [str(path) for path in removed]}, 0


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-freecad")
    verbs = parser.add_subparsers(dest="verb", required=True)
    for verb in ("install", "uninstall"):
        command = verbs.add_parser(verb)
        command.add_argument("--project", type=Path, required=True)
        command.add_argument("--json", action="store_true", dest="as_json")
        command.add_argument(
            "--yes", action="store_true", help="Accepted for symmetry; never prompts."
        )
        if verb == "install":
            command.add_argument(
                "--dcc-path", type=Path, help="FreeCAD app, FreeCAD.exe or FreeCADCmd"
            )
            command.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv))
    project = args.project.expanduser().absolute()
    if args.verb == "install":
        report, code = install(project, args.dcc_path, args.timeout)
    else:
        report, code = uninstall(project)
    print(
        json.dumps(report, sort_keys=True)
        if args.as_json
        else "%s: %s" % (args.verb, report["status"])
    )
    return code
