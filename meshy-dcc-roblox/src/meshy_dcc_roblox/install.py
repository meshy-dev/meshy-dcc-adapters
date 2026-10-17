"""Install the Studio plugin and bind a project to one Roblox place.

The plugin is one Luau file in Studio's local plugins folder, shared by every
place the user opens. A project is a directory holding one local place file
(``.rbxl``/``.rbxlx``), or bound to a published place by its ids;
``.meshy-dcc/`` inside it records the place and the start-instance launch
plan, whose executable is this package's Python running ``launch``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from .__version__ import __version__

PLUGIN_FILE = "MeshyDcc.lua"
PLUGIN_MARKER = "-- Meshy DCC for Roblox Studio"
PLUGIN_SOURCE = Path(__file__).resolve().parent / "plugin" / PLUGIN_FILE
CONFIG = Path(".meshy-dcc") / "roblox.json"
LAUNCH_PLAN = Path(".meshy-dcc") / "launch-plan.json"
PLACE_SUFFIXES = (".rbxl", ".rbxlx")


class InstallError(Exception):
    pass


def plugins_dir() -> Path:
    """Studio's local plugins folder (``MESHY_DCC_ROBLOX_PLUGINS_DIR`` overrides)."""
    override = os.environ.get("MESHY_DCC_ROBLOX_PLUGINS_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(os.environ["LOCALAPPDATA"]) / "Roblox" / "Plugins"
    return Path.home() / "Documents" / "Roblox" / "Plugins"


def _ours(path: Path) -> bool:
    with path.open(encoding="utf-8", errors="replace") as handle:
        return handle.readline().startswith(PLUGIN_MARKER)


def _write(path: Path, text: str) -> None:
    """Replace ``path`` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _place_file(project: Path, place: Optional[str]) -> str:
    if place:
        path = (project / place).absolute()
        if path.parent != project or path.suffix.lower() not in PLACE_SUFFIXES or not path.is_file():
            raise InstallError(f"--place must name a .rbxl or .rbxlx file directly inside {project}")
        return path.name
    found = sorted(p.name for p in project.iterdir() if p.suffix.lower() in PLACE_SUFFIXES and p.is_file())
    if len(found) != 1:
        raise InstallError(
            f"{project} holds {len(found)} place files ({', '.join(found) or 'none'}); keep exactly "
            "one .rbxl/.rbxlx there (in Studio: File > Save to File As), or pass --place, "
            "or --place-id and --universe-id for a published place."
        )
    return found[0]


def install(
    project: Path,
    place: Optional[str] = None,
    place_id: Optional[int] = None,
    universe_id: Optional[int] = None,
) -> dict:
    project = project.absolute()
    if not project.is_dir():
        raise InstallError(f"--project must be an existing directory: {project}")
    if (place_id is None) != (universe_id is None):
        raise InstallError("--place-id and --universe-id go together")
    binding = (
        {"place_id": place_id, "universe_id": universe_id}
        if place_id is not None
        else {"place_file": _place_file(project, place)}
    )
    plugin = plugins_dir() / PLUGIN_FILE
    if plugin.exists() and not _ours(plugin):
        raise InstallError(f"{plugin} exists and is not the Meshy DCC plugin; it was left alone")
    _write(plugin, PLUGIN_SOURCE.read_text(encoding="utf-8"))

    _write(project / ".meshy-dcc" / ".gitignore", "*\n")
    config = {"version": __version__, "plugin": str(plugin), **binding}
    _write(project / CONFIG, json.dumps(config, indent=2) + "\n")
    markers = [CONFIG.as_posix()] + ([binding["place_file"]] if "place_file" in binding else [])
    plan = {
        "schema_version": 1,
        "dcc_type": "roblox",
        # Not .resolve(): a venv's python is a symlink, and following it leaves the venv.
        "executable": str(Path(sys.executable).absolute()),
        "argv": ["{executable}", "-I", "-m", "meshy_dcc_roblox", "launch", "--project", "{project}"],
        "project_markers": markers,
    }
    _write(project / LAUNCH_PLAN, json.dumps(plan, indent=2) + "\n")
    return {"installed": True, "plugin": str(plugin), "project": str(project), **binding}


def uninstall(project: Optional[Path] = None, plugin: bool = False) -> dict:
    removed = []
    if project is not None:
        project = project.absolute()
        plan_path = project / LAUNCH_PLAN
        if plan_path.is_file() and json.loads(plan_path.read_text(encoding="utf-8")).get("dcc_type") == "roblox":
            plan_path.unlink()
            removed.append(str(plan_path))
        for path in (project / CONFIG, project / ".meshy-dcc" / ".gitignore"):
            if path.is_file():
                path.unlink()
                removed.append(str(path))
        meta = project / ".meshy-dcc"
        if meta.is_dir() and not any(meta.iterdir()):
            meta.rmdir()
    if plugin:
        path = plugins_dir() / PLUGIN_FILE
        if path.is_file() and _ours(path):
            path.unlink()
            removed.append(str(path))
    return {"removed": removed}


def status(project: Optional[Path] = None) -> dict:
    plugin = plugins_dir() / PLUGIN_FILE
    report = {
        "version": __version__,
        "plugin": str(plugin),
        "plugin_installed": plugin.is_file() and _ours(plugin),
        "plugin_current": plugin.is_file()
        and plugin.read_text(encoding="utf-8") == PLUGIN_SOURCE.read_text(encoding="utf-8"),
    }
    if project is not None:
        config = project.absolute() / CONFIG
        report["project"] = json.loads(config.read_text(encoding="utf-8")) if config.is_file() else None
    return report


def read_config(project: Path) -> dict:
    path = project.absolute() / CONFIG
    if not path.is_file():
        raise InstallError(f"{project} is not set up for Roblox; run install --project first")
    return json.loads(path.read_text(encoding="utf-8"))
