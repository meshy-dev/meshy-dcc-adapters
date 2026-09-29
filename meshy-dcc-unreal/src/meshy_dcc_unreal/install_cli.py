"""Set up an Unreal project for Meshy DCC.

``install`` copies the plugin to ``<project>/Plugins/MeshyDccUnreal``. The
plugin carries its Python dependencies (this adapter and ``meshy_dcc_core``)
in ``python/``, so nothing is installed into the engine and the editor's own
Python runs them. Project plugins are enabled by default, so the ``.uproject``
file is left alone.

``install`` also writes ``.meshy-dcc/`` next to the ``.uproject``:
``launch-plan.json`` for ``meshy-dcc start-instance`` and
``receipts/unreal.json``, the SHA-256 of every plugin file it wrote. The
directory ignores itself for version control. Repair, upgrade and uninstall
only touch plugin files the receipt owns, and they refuse while the plugin
holds anything else, apart from Python's ``__pycache__``.

``meshy-dcc install --dcc-type unreal --project <root>`` runs this from the
Meshy DCC package with its own Python. Without ``--yes`` nothing is written
and the report is a plan. Exit codes: 0 done, 10 preflight, 30 the change
failed and was rolled back, 50 the change is done but a copy was left behind.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from meshy_dcc_unreal.__version__ import __version__

DCC_TYPE = "unreal"
PLUGIN_NAME = "MeshyDccUnreal"
DESCRIPTOR_NAME = f"{PLUGIN_NAME}.uplugin"
MIN_ENGINE_VERSION = (5, 0, 0)
ENGINE_ENV = "MESHY_DCC_UNREAL_ENGINE"
PAYLOAD_ENV = "MESHY_DCC_UNREAL_PAYLOAD"
STATE_DIR = ".meshy-dcc"
LAUNCH_PLAN = "launch-plan.json"
RECEIPT = Path("receipts") / "unreal.json"
RECEIPT_TYPE = "meshy-dcc-install-receipt"
GITIGNORE_CONTENT = "*\n"

EXIT_OK = 0
EXIT_PREFLIGHT = 10
EXIT_INSTALL = 30
EXIT_LEFT_BEHIND = 50


class InstallError(Exception):
    def __init__(self, message: str, code: int = EXIT_PREFLIGHT, **fields: Any) -> None:
        super().__init__(message)
        self.code = code
        self.fields = fields


# --- project and engine ---------------------------------------------------


def find_project_file(project: Path) -> Path:
    project = project.expanduser().absolute()
    if project.is_file() and project.suffix == ".uproject":
        return project
    if not project.is_dir():
        raise InstallError(f"Not an Unreal project: {project}")
    found = sorted(project.glob("*.uproject"))
    if len(found) != 1:
        raise InstallError(f"Expected exactly one .uproject in {project}, found {len(found)}")
    return found[0]


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"Cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise InstallError(f"{path.name} is not a JSON object")
    return value


def _launcher_installs() -> Dict[str, Path]:
    """Engine installs the Epic Games Launcher knows about, by app name (``UE_5.7``)."""
    if sys.platform == "darwin":
        dat = Path.home() / "Library/Application Support/Epic/UnrealEngineLauncher/LauncherInstalled.dat"
    elif sys.platform == "win32":
        dat = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Epic/UnrealEngineLauncher/LauncherInstalled.dat"
    else:
        return {}
    try:
        entries = json.loads(dat.read_text(encoding="utf-8")).get("InstallationList", [])
    except (OSError, ValueError, AttributeError):
        return {}
    return {
        str(entry.get("AppName")): Path(str(entry.get("InstallLocation")))
        for entry in entries
        if isinstance(entry, dict) and entry.get("AppName") and entry.get("InstallLocation")
    }


def _default_engine_root(association: str) -> Optional[Path]:
    if sys.platform == "darwin":
        return Path("/Users/Shared/Epic Games") / f"UE_{association}"
    if sys.platform == "win32":
        return Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Epic Games" / f"UE_{association}"
    return None


def engine_version(root: Path) -> Tuple[int, int, int]:
    build = read_json(root / "Engine" / "Build" / "Build.version")
    try:
        return int(build["MajorVersion"]), int(build["MinorVersion"]), int(build["PatchVersion"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InstallError(f"Unreadable Engine/Build/Build.version under {root}") from exc


def editor_executable(root: Path) -> Path:
    binaries = root / "Engine" / "Binaries"
    if sys.platform == "darwin":
        return binaries / "Mac" / "UnrealEditor.app" / "Contents" / "MacOS" / "UnrealEditor"
    if sys.platform == "win32":
        return binaries / "Win64" / "UnrealEditor.exe"
    return binaries / "Linux" / "UnrealEditor"


def find_engine(project: Dict[str, Any], override: Optional[str]) -> Dict[str, Any]:
    """The engine for this project: ``--engine``, ``MESHY_DCC_UNREAL_ENGINE``, then EngineAssociation."""
    association = str(project.get("EngineAssociation") or "").strip()
    explicit = override or os.environ.get(ENGINE_ENV)
    if explicit:
        root = Path(explicit).expanduser().absolute()
    elif re.fullmatch(r"\d+\.\d+", association):
        root = _launcher_installs().get(f"UE_{association}") or _default_engine_root(association)
        if root is None or not root.is_dir():
            raise InstallError(
                f"Unreal Engine {association} is not installed where the Epic Games Launcher puts it; "
                f"pass --engine or set {ENGINE_ENV} to the engine root"
            )
    else:
        raise InstallError(
            f"The project's EngineAssociation {association or '(empty)'} names no installed engine; "
            f"pass --engine or set {ENGINE_ENV} to the engine root"
        )
    version = engine_version(root)
    if version < MIN_ENGINE_VERSION:
        raise InstallError(f"Unreal Engine {'.'.join(map(str, version))} is too old; 5.0 or newer is required")
    if re.fullmatch(r"\d+\.\d+", association) and tuple(map(int, association.split("."))) != version[:2]:
        raise InstallError(
            f"The project is for Unreal Engine {association}, but {root} is {'.'.join(map(str, version))}"
        )
    editor = editor_executable(root)
    if not editor.is_file():
        raise InstallError(f"Unreal Editor is missing: {editor}")
    return {"root": str(root), "version": ".".join(map(str, version)), "editor": str(editor)}


def check_project_plugins(project: Dict[str, Any]) -> None:
    """Refuse a project that switched off this plugin or the Python plugin it needs."""
    for entry in project.get("Plugins") or []:
        if not isinstance(entry, dict) or entry.get("Enabled") is not False:
            continue
        if entry.get("Name") in (PLUGIN_NAME, "PythonScriptPlugin", "EditorScriptingUtilities"):
            raise InstallError(
                f"The project disables {entry['Name']}, which Meshy DCC needs; enable it in the .uproject first"
            )


# --- files ------------------------------------------------------------------


def payload_root() -> Path:
    """The plugin to copy: the one this package was loaded from, or ``MESHY_DCC_UNREAL_PAYLOAD``."""
    override = os.environ.get(PAYLOAD_ENV)
    root = Path(override) if override else Path(__file__).resolve().parents[2]
    if not (root / DESCRIPTOR_NAME).is_file():
        raise InstallError(f"No {DESCRIPTOR_NAME} in {root}; run the installer from the Meshy DCC package")
    return root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_cache(relative: Path) -> bool:
    return "__pycache__" in relative.parts


def manifest(root: Path) -> Dict[str, str]:
    """SHA-256 of every file below ``root`` except Python caches; links are refused."""
    files: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if _is_cache(relative):
            continue
        if path.is_symlink():
            raise InstallError(f"Refusing a symbolic link in the plugin: {relative.as_posix()}")
        if path.is_file():
            files[relative.as_posix()] = _sha256(path)
    return files


def foreign_files(root: Path, owned: Dict[str, str]) -> List[str]:
    """Files below ``root`` the receipt does not own, or owns with other content."""
    if not root.exists():
        return []
    try:
        current = manifest(root)
    except InstallError as exc:
        return [str(exc)]
    return sorted(name for name, digest in current.items() if owned.get(name) != digest)


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _snapshot(path: Path) -> Optional[bytes]:
    return path.read_bytes() if path.is_file() else None


def _restore(path: Path, content: Optional[bytes]) -> None:
    if content is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def read_receipt(state: Path) -> Optional[Dict[str, Any]]:
    path = state / RECEIPT
    if not path.is_file():
        return None
    receipt = read_json(path)
    if receipt.get("type") != RECEIPT_TYPE or receipt.get("dcc_type") != DCC_TYPE:
        raise InstallError(f"{path} is not a Meshy DCC Unreal receipt")
    if not isinstance(receipt.get("files"), dict):
        raise InstallError(f"{path} lists no files")
    return receipt


def _launch_plan(project_file: Path, engine: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "dcc_type": DCC_TYPE,
        "executable": engine["editor"],
        "argv": ["{executable}", "{project}/" + project_file.name],
        "version": engine["version"],
        "project_markers": [project_file.name, f"Plugins/{PLUGIN_NAME}/{DESCRIPTOR_NAME}"],
    }


def _remove_empty_dirs(root: Path, stop: Path) -> None:
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    while root != stop and root.is_dir() and not any(root.iterdir()):
        root.rmdir()
        root = root.parent


# --- verbs ------------------------------------------------------------------


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        self.project_file = find_project_file(Path(args.project))
        self.project = read_json(self.project_file)
        self.root = self.project_file.parent
        self.plugin = self.root / "Plugins" / PLUGIN_NAME
        self.state = self.root / STATE_DIR
        self.receipt = read_receipt(self.state)

    def report(self, **fields: Any) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "dcc_type": DCC_TYPE,
            "adapter_version": __version__,
            "project": str(self.project_file),
            "plugin": str(self.plugin),
            "receipt": str(self.state / RECEIPT),
            **fields,
        }


def _owned(context: Context) -> Dict[str, str]:
    return dict(context.receipt["files"]) if context.receipt else {}


def _refuse_foreign(context: Context, action: str) -> None:
    if context.plugin.exists() and context.receipt is None:
        raise InstallError(
            f"{context.plugin} was not installed by meshy-dcc-unreal; move it out of Plugins/, then {action} again"
        )
    foreign = foreign_files(context.plugin, _owned(context))
    if foreign:
        raise InstallError(
            f"{context.plugin} holds files meshy-dcc-unreal did not write or that changed since; "
            f"move them out, then {action} again",
            files=foreign,
        )


def install(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    context = Context(args)
    check_project_plugins(context.project)
    engine = find_engine(context.project, args.engine)
    source = payload_root()
    payload = manifest(source)
    descriptor = read_json(source / DESCRIPTOR_NAME)
    if descriptor.get("VersionName") != __version__:
        raise InstallError(f"The packaged plugin is {descriptor.get('VersionName')}, not {__version__}")
    _refuse_foreign(context, "install")

    receipt = context.receipt
    if not context.plugin.exists():
        mode = "fresh"
    elif receipt and receipt.get("adapter_version") == __version__ and manifest(context.plugin) == payload:
        mode = "current"
    elif receipt and receipt.get("adapter_version") == __version__:
        mode = "repair"
    else:
        mode = "upgrade"
    plan = _launch_plan(context.project_file, engine)
    if not args.yes:
        return EXIT_OK, context.report(status="planned", install_mode=mode, engine=engine)

    launch_path = context.state / LAUNCH_PLAN
    gitignore = context.state / ".gitignore"
    saved = {path: _snapshot(path) for path in (launch_path, gitignore, context.state / RECEIPT)}
    token = uuid.uuid4().hex
    staging = context.state / f"staging-{token}"
    previous = context.state / f"previous-{token}"
    moved = placed = False
    try:
        if mode != "current":
            context.state.mkdir(exist_ok=True)
            shutil.copytree(source, staging, ignore=shutil.ignore_patterns("__pycache__"))
            if manifest(staging) != payload:
                raise InstallError("The staged plugin differs from the package", EXIT_INSTALL)
            if context.plugin.exists():
                os.replace(context.plugin, previous)
                moved = True
            context.plugin.parent.mkdir(exist_ok=True)
            os.replace(staging, context.plugin)
            placed = True
        _write_json(launch_path, plan)
        gitignore.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        _write_json(
            context.state / RECEIPT,
            {
                "schema_version": 1,
                "type": RECEIPT_TYPE,
                "dcc_type": DCC_TYPE,
                "adapter_version": __version__,
                "project_file": context.project_file.name,
                "plugin_path": f"Plugins/{PLUGIN_NAME}",
                "engine": {"root": engine["root"], "version": engine["version"]},
                "files": payload,
            },
        )
    except (OSError, InstallError) as exc:
        if placed:
            shutil.rmtree(context.plugin)
        if moved:
            os.replace(previous, context.plugin)
        for path, content in saved.items():
            _restore(path, content)
        raise InstallError(f"Install failed and was rolled back: {exc}", EXIT_INSTALL) from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    result = context.report(status="ok", install_mode=mode, engine=engine, launch_plan=str(launch_path))
    if moved:
        # Checked above, but a writer could have raced in since; keep the copy then.
        # ponytail: a write landing between this check and rmtree is lost; the window is milliseconds.
        left = foreign_files(previous, _owned(context))
        if left:
            result.update(
                status="left_behind",
                previous_copy=str(previous),
                files=left,
                message=f"The previous plugin copy at {previous} holds files that changed during the install. "
                "Move out anything to keep, then delete it.",
            )
            return EXIT_LEFT_BEHIND, result
        shutil.rmtree(previous)
    return EXIT_OK, result


def uninstall(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    context = Context(args)
    if context.receipt is None and not context.plugin.exists():
        return EXIT_OK, context.report(status="absent")
    _refuse_foreign(context, "uninstall")
    if not args.yes:
        return EXIT_OK, context.report(status="planned")
    if context.plugin.exists():
        removing = context.state / f"removing-{uuid.uuid4().hex}"
        os.replace(context.plugin, removing)
        shutil.rmtree(removing)
    launch_path = context.state / LAUNCH_PLAN
    if launch_path.is_file() and read_json(launch_path).get("dcc_type") == DCC_TYPE:
        launch_path.unlink()
    (context.state / RECEIPT).unlink(missing_ok=True)
    gitignore = context.state / ".gitignore"
    if gitignore.is_file() and gitignore.read_text(encoding="utf-8") == GITIGNORE_CONTENT:
        remaining = [p for p in context.state.rglob("*") if p.is_file() and p != gitignore]
        if not remaining:
            gitignore.unlink()
    _remove_empty_dirs(context.state, context.root)
    plugins = context.plugin.parent
    if plugins.is_dir() and not any(plugins.iterdir()):
        plugins.rmdir()
    return EXIT_OK, context.report(status="removed")


def status(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    context = Context(args)
    if context.receipt is None:
        state = "unowned" if context.plugin.exists() else "absent"
        return EXIT_OK, context.report(status=state)
    foreign = foreign_files(context.plugin, _owned(context))
    missing = sorted(set(_owned(context)) - set(manifest(context.plugin) if context.plugin.exists() else {}))
    state = "modified" if foreign else "incomplete" if missing else "installed"
    return EXIT_OK, context.report(
        status=state,
        installed_version=context.receipt.get("adapter_version"),
        files=foreign or missing,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meshy-dcc-unreal", description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    for verb in ("install", "uninstall", "status"):
        sub = verbs.add_parser(verb)
        sub.add_argument("project", help="Project directory or .uproject file")
        sub.add_argument("--json", action="store_true", help="Print the report as JSON")
        if verb != "status":
            sub.add_argument("--yes", action="store_true", help="Make the change; without it, only plan")
        if verb == "install":
            sub.add_argument("--engine", help=f"Engine root (default: {ENGINE_ENV}, then EngineAssociation)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        code, report = {"install": install, "uninstall": uninstall, "status": status}[args.verb](args)
    except InstallError as exc:
        code = exc.code
        report = {"schema_version": 1, "dcc_type": DCC_TYPE, "status": "failed", "message": str(exc), **exc.fields}
    if report.get("message"):
        # meshy-dcc shows the stderr tail of a failed step.
        print(report["message"], *report.get("files", []), sep="\n", file=sys.stderr)
    print(json.dumps(report, indent=2) if args.json else f"{report['status']}: {report.get('plugin', '')}")
    return code


if __name__ == "__main__":
    sys.exit(main())
