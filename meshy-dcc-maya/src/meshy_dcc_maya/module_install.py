"""Point Maya at the Meshy DCC module, or stop pointing at it.

``meshy-dcc install --dcc-type maya`` extracts the package and runs this
script with the package's own CPython (``bin/meshy-dcc-maya``)::

    meshy-dcc-maya install --json      write <modules dir>/meshy_dcc_maya.mod
    meshy-dcc-maya uninstall --json    remove it again

The ``.mod`` file is the only thing written outside the package: one line
naming the module folder next to this file's package, plus its ``python``
folder for ``PYTHONPATH``. Maya adds the module's ``plug-ins`` and
``scripts`` folders by itself, and runs the module's ``scripts/userSetup.py``
at startup, which loads the plug-in. The user's own ``userSetup.py`` and
preferences are never touched.

The modules directory is ``MESHY_DCC_MAYA_MODULES_DIR`` when set, else
``$MAYA_APP_DIR/modules``, else Maya's default per-user folder:
``~/Library/Preferences/Autodesk/maya/modules`` on macOS and
``<Documents>/maya/modules`` on Windows (the Documents known folder, which
may be redirected, for example to OneDrive).

Standard library only: it runs with ``python -I`` before Maya is involved.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

MOD_NAME = "meshy_dcc_maya"
MOD_FILE = MOD_NAME + ".mod"
MODULE_VERSION = "0.1.0"
MODULE_DIR = Path(os.path.abspath(__file__)).parents[2]  # abspath folds the launcher's "bin/.."
REQUIRED = (
    "plug-ins/meshy_dcc_maya_plugin.py",
    "scripts/userSetup.py",
    "python/meshy_dcc_maya/__init__.py",
    "python/meshy_dcc_core/__init__.py",
)


def _windows_documents() -> Path:
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
    folder = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
    path = ctypes.c_wchar_p()
    shell32 = ctypes.windll.shell32
    if shell32.SHGetKnownFolderPath(ctypes.byref(folder), 0, None, ctypes.byref(path)) != 0:
        return Path.home() / "Documents"
    try:
        return Path(path.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path)


def modules_dir(environ=os.environ, platform: str = sys.platform) -> Path:
    """The per-user folder Maya searches for ``.mod`` files."""
    override = environ.get("MESHY_DCC_MAYA_MODULES_DIR", "").strip()
    if override:
        return Path(override)
    app_dir = environ.get("MAYA_APP_DIR", "").strip()
    if app_dir:
        return Path(app_dir) / "modules"
    if platform == "darwin":
        return Path.home() / "Library" / "Preferences" / "Autodesk" / "maya" / "modules"
    if platform == "win32":
        return _windows_documents() / "maya" / "modules"
    return Path.home() / "maya" / "modules"


def mod_text(module_dir: Path) -> str:
    return "+ {} {} {}\nPYTHONPATH+:=python\n".format(MOD_NAME, MODULE_VERSION, module_dir.as_posix())


def is_ours(path: Path) -> bool:
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return False
    return first.startswith("+ {} ".format(MOD_NAME))


def install(target_dir: Path, module_dir: Path = MODULE_DIR) -> dict:
    missing = [item for item in REQUIRED if not (module_dir / item).is_file()]
    if missing:
        raise RuntimeError("the module folder {} is incomplete: missing {}".format(module_dir, ", ".join(missing)))
    path = target_dir / MOD_FILE
    if path.exists() and not is_ours(path):
        raise RuntimeError("{} exists and was not written by Meshy DCC; move it away first".format(path))
    target_dir.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=".meshy_dcc_maya-", suffix=".tmp", dir=str(target_dir))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(mod_text(module_dir))
        os.replace(temp, str(path))
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise
    return {"mod_file": str(path), "module_dir": str(module_dir)}


def uninstall(target_dir: Path) -> dict:
    path = target_dir / MOD_FILE
    if not path.exists():
        return {"mod_file": str(path), "removed": False}
    if not is_ours(path):
        raise RuntimeError("{} was not written by Meshy DCC; leaving it in place".format(path))
    path.unlink()
    return {"mod_file": str(path), "removed": True}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-maya", description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--json", action="store_true", help="print a JSON report on stdout")
    args = parser.parse_args(argv)
    try:
        target = modules_dir()
        report = install(target) if args.action == "install" else uninstall(target)
        report.update(ok=True, action=args.action)
        code = 0
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        report = {"ok": False, "action": args.action, "error": str(exc)}
        code = 1
        print("meshy-dcc-maya {}: {}".format(args.action, exc), file=sys.stderr)
    if args.json:
        print(json.dumps(report))
    elif code == 0:
        print("{}: {}".format(args.action, report["mod_file"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
