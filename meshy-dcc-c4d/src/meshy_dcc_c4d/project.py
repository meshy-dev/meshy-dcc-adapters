"""Bind a folder to a Cinema 4D runtime for ``meshy-dcc start-instance``.

A Cinema 4D "project" is a working folder: the service started for it may only
read and write ``.c4d`` documents, imports, exports and renders inside it.
``install --project`` records two files under ``<project>/.meshy-dcc/``:

``launch-plan.json``
    How start-instance starts this adapter's service for the folder. The
    executable is the Python that ran the installer (the package's own Python),
    so the plan never goes through a shell script or ``.cmd``.
``c4d.json``
    The licensed ``c4dpy`` the service runs each operation with.

``.meshy-dcc/`` ignores itself for version control. Nothing is written to the
Cinema 4D installation or the user's Cinema 4D preferences.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from .__version__ import __version__
from .bridge import Cinema4dBridge

DCC_TYPE = "c4d"
OWNER = "meshy-dcc-c4d"
STATE_DIR = ".meshy-dcc"
LAUNCH_PLAN = Path(STATE_DIR) / "launch-plan.json"
CONFIG = Path(STATE_DIR) / "c4d.json"
_IGNORE = "*\n"


class ProjectError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2) + "\n")
        os.replace(temporary, str(path))
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _project_root(project: Path) -> Path:
    root = project.expanduser().absolute()
    if not root.is_dir():
        raise ProjectError("project_missing", "Project folder does not exist: %s" % root)
    state = root / STATE_DIR
    if state.is_symlink() or (state.exists() and not state.is_dir()):
        raise ProjectError("unsafe_state_dir", "%s must be a real folder" % state)
    return root


def resolve_c4dpy(value: Path) -> Path:
    """The canonical ``c4dpy`` named by a file, ``c4dpy.app`` or an install folder."""
    if value.suffix.lower() == ".app":
        value = value / "Contents" / "MacOS" / value.stem
    found = Cinema4dBridge._resolve_executable(str(value))
    if found is None or Path(found).name.lower() not in {"c4dpy", "c4dpy.exe"}:
        raise ProjectError(
            "c4dpy_invalid",
            "Not a c4dpy executable: %s. Pass Cinema 4D's c4dpy (for example "
            "'/Applications/Maxon Cinema 4D 2026/c4dpy.app' or "
            "'C:/Program Files/Maxon Cinema 4D 2026/c4dpy.exe')." % value,
        )
    return Path(found)


def launch_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dcc_type": DCC_TYPE,
        "executable": str(Path(sys.executable).absolute()),
        "argv": ["{executable}", "-I", "-m", "meshy_dcc_c4d", "serve", "--project", "{project}"],
        "project_markers": [CONFIG.as_posix()],
    }


def install_project(project: Path, c4dpy: Path, *, execute: bool) -> dict[str, Any]:
    root = _project_root(project)
    executable = resolve_c4dpy(c4dpy)
    existing = _read_json(root / LAUNCH_PLAN)
    if (root / LAUNCH_PLAN).exists() and (existing or {}).get("dcc_type") != DCC_TYPE:
        raise ProjectError(
            "foreign_launch_plan",
            "%s belongs to another adapter; choose a folder of its own for Cinema 4D"
            % (root / LAUNCH_PLAN),
        )
    result = {
        "status": "ok" if execute else "planned",
        "operation": "install",
        "dcc_type": DCC_TYPE,
        "adapter_version": __version__,
        "project": str(root),
        "c4dpy": str(executable),
        "files": [LAUNCH_PLAN.as_posix(), CONFIG.as_posix()],
    }
    if not execute:
        return result
    (root / STATE_DIR).mkdir(exist_ok=True)
    ignore = root / STATE_DIR / ".gitignore"
    if not ignore.exists():
        ignore.write_text(_IGNORE, encoding="utf-8")
    config = {
        "schema_version": 1,
        "owner": OWNER,
        "adapter_version": __version__,
        "c4dpy": str(executable),
    }
    _atomic_write(root / CONFIG, config)
    _atomic_write(root / LAUNCH_PLAN, launch_plan())
    return result


def uninstall_project(project: Path, *, execute: bool) -> dict[str, Any]:
    """Remove only the files ``install --project`` wrote; the documents stay."""
    root = _project_root(project)
    removable = []
    if (_read_json(root / CONFIG) or {}).get("owner") == OWNER:
        removable.append(CONFIG)
    if (_read_json(root / LAUNCH_PLAN) or {}).get("dcc_type") == DCC_TYPE:
        removable.append(LAUNCH_PLAN)
    result = {
        "status": "ok" if execute else "planned",
        "operation": "uninstall",
        "dcc_type": DCC_TYPE,
        "project": str(root),
        "files": [path.as_posix() for path in removable],
    }
    if not execute:
        return result
    for path in removable:
        (root / path).unlink()
    state = root / STATE_DIR
    ignore = state / ".gitignore"
    if state.is_dir() and {item.name for item in state.iterdir()} <= {".gitignore"}:
        if ignore.exists() and ignore.read_text(encoding="utf-8") == _IGNORE:
            ignore.unlink()
        if not any(state.iterdir()):
            state.rmdir()
    return result


def configured_c4dpy(project: Path) -> Optional[str]:
    config = _read_json(project / CONFIG) or {}
    value = config.get("c4dpy") if config.get("owner") == OWNER else None
    return value if isinstance(value, str) and value else None
