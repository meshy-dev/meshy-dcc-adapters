"""Set up a material project folder for ``meshy-dcc start-instance``.

``install-project <folder> --dcc-path <Material Maker> --sidecar <launcher>``
writes ``<folder>/.meshy-dcc/``:

- ``launch-plan.json``: start-instance runs the sidecar bound to the folder;
- ``material-maker.json``: the Material Maker executable the tools run;
- ``.gitignore``: the directory ignores itself;
- ``receipts/material-maker.json``: the SHA-256 of each file written.

Without ``--yes`` it only reports the plan. Files another adapter or the user
wrote are never replaced, and ``uninstall-project`` removes only files whose
content still matches the receipt. Material Maker itself is never touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Optional, Sequence

from .__version__ import __version__

DCC_TYPE = "material-maker"
STATE_DIR = ".meshy-dcc"
CONFIG = "material-maker.json"
LAUNCH_PLAN = "launch-plan.json"
GITIGNORE = ".gitignore"
RECEIPT = "receipts/material-maker.json"


class ProjectInstallError(RuntimeError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def read_project_config(project: Path) -> dict[str, Any]:
    """The recorded Material Maker settings of a project, or {} if none."""
    try:
        value = json.loads((project / STATE_DIR / CONFIG).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def material_maker_executable(value: str) -> Path:
    """The Material Maker binary behind a path, which may be a macOS ``.app``."""
    from .bridge import _app_bundle_executable

    path = _app_bundle_executable(Path(value).expanduser()).resolve()
    if not path.is_file():
        raise ProjectInstallError("material_maker_not_found", "Material Maker not found at %s" % value)
    # Material Maker keeps its node library next to its executable.
    if not (path.parent / "nodes" / "material.mmg").is_file():
        raise ProjectInstallError(
            "not_material_maker", "%s has no Material Maker node library beside it" % path
        )
    return path


def _receipt(project: Path) -> dict[str, str]:
    try:
        value = json.loads((project / STATE_DIR / RECEIPT).read_text(encoding="utf-8"))
        return {item["path"]: item["sha256"] for item in value["owned_files"]}
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        return {}


def planned_files(executable: Path, sidecar: Path) -> dict[str, bytes]:
    return {
        LAUNCH_PLAN: _json(
            {
                "schema_version": 1,
                "dcc_type": DCC_TYPE,
                "executable": str(sidecar),
                "argv": ["{executable}", "serve", "--project", "{project}"],
                "project_markers": [STATE_DIR + "/" + CONFIG],
            }
        ),
        CONFIG: _json(
            {
                "schema_version": 1,
                "dcc_type": DCC_TYPE,
                "adapter_version": __version__,
                "executable": str(executable),
            }
        ),
        GITIGNORE: b"*\n",
    }


def install(project: Path, executable: Path, sidecar: Path, *, apply: bool) -> list[dict[str, str]]:
    state = project / STATE_DIR
    owned = _receipt(project)
    steps = []
    files = planned_files(executable, sidecar)
    for name, data in files.items():
        target = state / name
        if target.is_symlink():
            raise ProjectInstallError("unsafe_path", "%s is a symbolic link" % target)
        if target.exists():
            current = target.read_bytes()
            if current == data:
                steps.append({"id": name, "status": "current"})
                continue
            if name == GITIGNORE:
                # Someone else's ignore rules: leave them.
                steps.append({"id": name, "status": "kept"})
                continue
            if owned.get(name) != _sha256(current):
                raise ProjectInstallError(
                    "file_not_owned",
                    "%s was not written by this adapter (another adapter may own this "
                    "folder); use a separate folder for materials" % target,
                )
        steps.append({"id": name, "status": "written" if apply else "planned"})
    if apply:
        (state / "receipts").mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            if not any(s["id"] == name and s["status"] == "kept" for s in steps):
                _atomic_write(state / name, data)
        receipt = {
            "receipt_version": 1,
            "dcc_type": DCC_TYPE,
            "adapter_version": __version__,
            "owned_files": [
                {"path": name, "sha256": _sha256(data)}
                for name, data in files.items()
                if (state / name).read_bytes() == data
            ],
        }
        _atomic_write(state / RECEIPT, _json(receipt))
    return steps


def uninstall(project: Path, *, apply: bool) -> list[dict[str, str]]:
    state = project / STATE_DIR
    steps = []
    for name, digest in _receipt(project).items():
        target = state / name
        if not target.is_file() or target.is_symlink():
            steps.append({"id": name, "status": "absent"})
        elif _sha256(target.read_bytes()) != digest:
            steps.append({"id": name, "status": "kept", "message": "changed since install"})
        else:
            steps.append({"id": name, "status": "removed" if apply else "planned"})
            if apply:
                target.unlink()
    if apply and (state / RECEIPT).is_file():
        (state / RECEIPT).unlink()
        for directory in (state / "receipts", state):
            try:
                directory.rmdir()
            except OSError:
                pass
    return steps


def _atomic_write(path: Path, data: bytes) -> None:
    staged = path.with_name(".%s.staged" % path.name)
    staged.write_bytes(data)
    os.replace(staged, path)


def _core_version() -> str:
    try:
        return metadata.version("meshy-dcc-core")
    except metadata.PackageNotFoundError:
        return "unavailable"


def report(project: Path, steps: list, status: str, failure: Optional[ProjectInstallError] = None) -> dict:
    """An Install SOP report (the shape ``meshy_dcc_core.deployment`` validates)."""
    return {
        "schema_version": 1,
        "status": status,
        "dcc_type": DCC_TYPE,
        "adapter_version": __version__,
        "core_version": _core_version(),
        "steps": steps,
        "next_steps": [],
        "receipt_path": str(project / STATE_DIR / RECEIPT),
        "verify": {
            "directly_usable": status == "ok",
            "failure_stage": "install" if failure else None,
            "failure_reason": failure.reason if failure else None,
        },
        **({"message": str(failure)} if failure else {}),
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-material-maker")
    parser.add_argument("command", choices=("install-project", "uninstall-project"))
    parser.add_argument("project", help="Absolute path of the material project folder")
    parser.add_argument("--dcc-path", help="Material Maker executable or .app (install-project)")
    parser.add_argument("--sidecar", help="Launcher start-instance runs (install-project)")
    parser.add_argument("--yes", action="store_true", help="Apply; without it only plan")
    parser.add_argument("--json", action="store_true", help="Print the JSON report")
    args = parser.parse_args(list(argv))
    project = Path(args.project).expanduser()
    steps: list = []
    try:
        if not project.is_absolute() or not project.is_dir():
            raise ProjectInstallError("project_not_found", "%s is not an existing absolute folder" % project)
        project = project.resolve()
        if args.command == "install-project":
            if not args.dcc_path or not args.sidecar:
                raise ProjectInstallError("invalid_arguments", "install-project needs --dcc-path and --sidecar")
            sidecar = Path(args.sidecar).expanduser()
            if not sidecar.is_absolute() or not sidecar.is_file():
                raise ProjectInstallError("sidecar_not_found", "--sidecar must be an absolute path to a file")
            steps = install(project, material_maker_executable(args.dcc_path), sidecar, apply=args.yes)
        else:
            steps = uninstall(project, apply=args.yes)
        result = report(project, steps, "ok" if args.yes else "planned")
        code = 0
    except (ProjectInstallError, OSError) as error:
        failure = error if isinstance(error, ProjectInstallError) else ProjectInstallError("io_error", str(error))
        result = report(project, steps, "failed", failure)
        code = 30
    if args.json:
        print(json.dumps(result, indent=2))
    elif code:
        print(result.get("message"), file=sys.stderr)
    return code
