"""Install or remove the 3ds Max startup script of a Meshy DCC package.

``meshy-dcc install --dcc-type 3dsmax`` extracts the package and runs, with
the package's own CPython (this module needs only the standard library)::

    bin/meshy-dcc-3dsmax.cmd install --dcc-path <3dsmax.exe> --yes --json
    bin/meshy-dcc-3dsmax.cmd uninstall --dcc-path <3dsmax.exe> --yes --json

The adapter and ``meshy_dcc_core`` stay in the package's ``payload/`` folder;
3ds Max loads them from there. ``install`` writes one MAXScript,
``meshy_dcc_3dsmax_startup.ms``, into the user startup folder of every
language this user has started 3ds Max <year> in::

    %LOCALAPPDATA%\\Autodesk\\3dsMax\\<year> - 64bit\\<language>\\scripts\\startup

``<year>`` comes from the 3ds Max folder name (``3ds Max 2025``). Nothing is
written into the 3ds Max install directory. ``uninstall`` removes that script
and the ``Meshy DCC-*.mcr`` macro files the adapter's menu defines, and only
files that carry the adapter's marker or name.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

STARTUP_SCRIPT_NAME = "meshy_dcc_3dsmax_startup.ms"
MARKER = "-- Managed by meshy-dcc-3dsmax."
# Macro files 3ds Max writes for the menu's macroScripts (category "Meshy DCC").
MACRO_GLOB = "Meshy DCC-MeshyDcc3dsmax_*.mcr"
# The original project's startup script; both loaded together is untested.
FOREIGN_STARTUP_NAMES = ("dcc_mcp_3dsmax_startup.ms",)
EXIT_PREFLIGHT = 10
EXIT_INSTALL = 30


class InstallError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = EXIT_PREFLIGHT) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def payload_dir() -> Path:
    """The package's ``payload/`` folder: the one this module was loaded from."""
    return Path(os.path.abspath(__file__)).parent.parent


def max_year(dcc_path: str) -> str:
    """The 3ds Max release year, read from its install folder name."""
    found = re.findall(r"3ds ?max (20\d\d)", str(dcc_path), flags=re.IGNORECASE)
    if not found:
        raise InstallError(
            "dcc_version_unknown",
            "Cannot tell the 3ds Max version from {}; expected a path under a '3ds Max <year>' folder.".format(
                dcc_path
            ),
        )
    return found[-1]


def user_root(year: str, env: Optional[dict] = None) -> Path:
    local = (env if env is not None else os.environ).get("LOCALAPPDATA")
    if not local:
        raise InstallError("localappdata_missing", "LOCALAPPDATA is not set.")
    return Path(local) / "Autodesk" / "3dsMax" / "{} - 64bit".format(year)


def language_dirs(root: Path) -> List[Path]:
    """Language folders (ENU, CHS, ...) that 3ds Max has set up for this user."""
    if not root.is_dir() or root.is_symlink():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and (p / "scripts").is_dir())


def startup_script(payload: Path) -> str:
    """The MAXScript that puts ``payload`` on ``sys.path`` and starts the adapter.

    The path travels base64-encoded, so the file stays ASCII and needs no
    MAXScript escaping whatever the user name or install folder holds.
    """
    encoded = base64.b64encode(str(payload).encode("utf-8")).decode("ascii")
    python = "\\n".join(
        [
            "import base64, os, sys",
            "payload = base64.b64decode('{}').decode('utf-8')".format(encoded),
            "if os.path.isdir(payload):",
            "    if payload not in sys.path: sys.path.insert(0, payload)",
            "    from meshy_dcc_3dsmax.max_bootstrap import startup",
            "    startup()",
            "else:",
            "    print('meshy-dcc-3dsmax: package folder is gone; reinstall with meshy-dcc install --dcc-type 3dsmax')",
        ]
    )
    return "\r\n".join(
        [
            MARKER,
            "-- Starts the Meshy DCC adapter from the package meshy-dcc installed.",
            "-- Remove it with: meshy-dcc-3dsmax.cmd uninstall --dcc-path <3dsmax.exe>",
            'python.Execute "{}\\n"'.format(python),
            "",
        ]
    )


def _owned(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and path.read_bytes().startswith(MARKER.encode("ascii"))
    except OSError:
        return False


def _write_atomic(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".meshy-dcc-tmp")
    temp.write_bytes(text.encode("ascii"))
    os.replace(str(temp), str(path))


def install(dcc_path: str, env: Optional[dict] = None, payload: Optional[Path] = None) -> dict:
    year = max_year(dcc_path)
    root = user_root(year, env)
    languages = language_dirs(root)
    if not languages:
        raise InstallError(
            "host_never_started",
            "3ds Max {} has not been started by this user yet ({} has no language folder). "
            "Start 3ds Max {} once, close it, then install again.".format(year, root, year),
        )
    payload = payload or payload_dir()
    if not (payload / "meshy_dcc_3dsmax").is_dir() or not (payload / "meshy_dcc_core").is_dir():
        raise InstallError("payload_missing", "{} does not hold meshy_dcc_3dsmax and meshy_dcc_core.".format(payload))
    text = startup_script(payload)
    targets = [language / "scripts" / "startup" / STARTUP_SCRIPT_NAME for language in languages]
    for target in targets:
        if target.parent.is_symlink() or target.is_symlink():
            raise InstallError("startup_dir_linked", "Refusing a linked startup folder or script: {}".format(target))
        if target.exists() and not _owned(target):
            raise InstallError(
                "startup_script_foreign",
                "{} exists and was not written by meshy-dcc-3dsmax; move it away first.".format(target),
            )
    warnings = [
        "{} is also installed ({}); running both adapters in one 3ds Max is untested.".format(name, language)
        for language in languages
        for name in FOREIGN_STARTUP_NAMES
        if (language / "scripts" / "startup" / name).exists()
    ]
    written = []
    try:
        for target in targets:
            target.parent.mkdir(exist_ok=True)
            _write_atomic(target, text)
            written.append(str(target))
    except OSError as exc:
        raise InstallError("write_failed", "Could not write {}: {}".format(target, exc), EXIT_INSTALL)
    return {
        "ok": True,
        "command": "install",
        "dcc_version": year,
        "payload": str(payload),
        "startup_scripts": written,
        "warnings": warnings,
        "next_step": "Start (or restart) 3ds Max {}; the adapter registers with meshy-dcc as it starts.".format(year),
    }


def uninstall(dcc_path: str, env: Optional[dict] = None) -> dict:
    year = max_year(dcc_path)
    removed, kept = [], []
    for language in language_dirs(user_root(year, env)):
        script = language / "scripts" / "startup" / STARTUP_SCRIPT_NAME
        if script.exists() or script.is_symlink():
            if _owned(script):
                script.unlink()
                removed.append(str(script))
            else:
                kept.append(str(script))
        macros = language / "usermacros"
        if macros.is_dir() and not macros.is_symlink():
            for macro in sorted(macros.glob(MACRO_GLOB)):
                if macro.is_file() and not macro.is_symlink():
                    macro.unlink()
                    removed.append(str(macro))
    result = {"ok": True, "command": "uninstall", "dcc_version": year, "removed": removed}
    if kept:
        result["warnings"] = ["Not written by meshy-dcc-3dsmax, left in place: {}".format(path) for path in kept]
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-3dsmax", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["install", "uninstall"])
    parser.add_argument("--dcc-path", required=True, help="3dsmax.exe of the 3ds Max to set up")
    parser.add_argument("--yes", action="store_true", help="Accepted for meshy-dcc; nothing asks")
    parser.add_argument("--json", action="store_true", help="Print one JSON object")
    args = parser.parse_args(argv)
    try:
        result = install(args.dcc_path) if args.command == "install" else uninstall(args.dcc_path)
        code = 0
    except InstallError as exc:
        result = {"ok": False, "command": args.command, "error": {"code": exc.code, "message": str(exc)}}
        code = exc.exit_code
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result.get("next_step") or result.get("error", {}).get("message") or "done")
    return code


if __name__ == "__main__":
    sys.exit(main())
