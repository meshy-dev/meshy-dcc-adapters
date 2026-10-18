"""Register an extracted Meshy DCC Houdini package with Houdini, or remove it.

``meshy-dcc install --dcc-type houdini`` extracts the release zip and runs
``bin/meshy-dcc-houdini install --dcc-path <houdini> --json``. That writes one
Houdini package file, ``<user prefs>/packages/meshy_dcc_houdini.json``, which
points Houdini at the extracted directory::

    houdini/    joins HOUDINI_PATH: pythonX.Ylibs/uiready.py starts the adapter
    lib/        joins PYTHONPATH: meshy_dcc_houdini and meshy_dcc_core

Nothing is written into the Houdini installation. ``uninstall`` deletes the
package file only when it points at this package directory.

The user preferences directory follows Houdini's own rule for the Houdini
version: ``HOUDINI_USER_PREF_DIR`` (``__HVER__`` replaced by ``X.Y``), else
``~/Library/Preferences/houdini/X.Y`` on macOS and ``$HOME/houdiniX.Y`` on
Windows, where Houdini's ``$HOME`` is the ``HOME`` variable when set and the
Documents folder otherwise. The version comes from ``MESHY_DCC_HOUDINI_VERSION``,
else the executable's path (``Houdini21.0.440``, ``Houdini 21.0.440``,
``Versions/21.0``), else on Windows the executable's version resource.

This module uses only the standard library: it runs on the package's own
CPython before Houdini is involved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

PACKAGE_FILE = "meshy_dcc_houdini.json"
ROOT_ENV = "MESHY_DCC_HOUDINI_ROOT"
VERSION_ENV = "MESHY_DCC_HOUDINI_VERSION"
_PATH_VERSION = re.compile(r"Houdini[^/\\]*?(\d+)\.(\d+)\.\d+", re.IGNORECASE)
_FRAMEWORK_VERSION = re.compile(r"[/\\]Versions[/\\](\d+)\.(\d+)(?:[/\\]|$)")
_SHORT_VERSION = re.compile(r"^\d+\.\d+$")


class PackageError(RuntimeError):
    """An install or uninstall that cannot proceed; the message says why."""


def package_root() -> Path:
    """The extracted package: ``lib/meshy_dcc_houdini/`` sits two levels below it."""
    return Path(__file__).resolve().parents[2]


def houdini_version(dcc_path: str, environ: Mapping[str, str] = os.environ) -> str:
    """``X.Y`` of the Houdini at ``dcc_path``: the override, its install path, or its file version."""
    override = environ.get(VERSION_ENV, "").strip()
    if override:
        if not _SHORT_VERSION.match(override):
            raise PackageError("{} must be MAJOR.MINOR, for example 21.0; got {!r}".format(VERSION_ENV, override))
        return override
    # /Applications/Houdini/Current links to a versioned directory.
    for path in (dcc_path, os.path.realpath(dcc_path)):
        match = _PATH_VERSION.search(path) or _FRAMEWORK_VERSION.search(path)
        if match:
            return "{}.{}".format(match.group(1), match.group(2))
    # Windows installs can go anywhere (D:\houdini); houdini.exe carries its version.
    file_version = _windows_file_version(dcc_path) if sys.platform == "win32" else None
    if file_version:
        return file_version
    raise PackageError(
        "Cannot tell the Houdini version from {}; set {}=MAJOR.MINOR (for example 21.0) and rerun".format(
            dcc_path, VERSION_ENV
        )
    )


def _windows_file_version(path: str) -> Optional[str]:
    """``X.Y`` from an executable's fixed file version (houdini.exe: 21.0.0.440)."""
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    version = ctypes.WinDLL("version")
    version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, wintypes.LPDWORD]
    version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID]
    version.VerQueryValueW.argtypes = [
        wintypes.LPCVOID,
        wintypes.LPCWSTR,
        ctypes.POINTER(wintypes.LPVOID),
        wintypes.PUINT,
    ]
    size = version.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    buffer = ctypes.create_string_buffer(size)
    pointer, length = wintypes.LPVOID(), wintypes.UINT(0)
    if not version.GetFileVersionInfoW(path, 0, size, buffer) or not version.VerQueryValueW(
        buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)
    ):
        return None
    # VS_FIXEDFILEINFO: signature, struct version, file version MS, file version LS, ...
    file_version_ms = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD * 4)).contents[2]
    return "{}.{}".format(file_version_ms >> 16, file_version_ms & 0xFFFF)


def _documents_dir(environ: Mapping[str, str]) -> Path:
    """The Windows Documents folder, which OneDrive may have moved."""
    try:
        import ctypes  # noqa: PLC0415

        buffer = ctypes.create_unicode_buffer(260)
        # SHGetFolderPathW(CSIDL_PERSONAL): the folder Houdini uses for $HOME.
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0 and buffer.value:
            return Path(buffer.value)
    except (AttributeError, OSError):
        pass
    return Path(environ.get("USERPROFILE") or Path.home()) / "Documents"


def user_pref_dir(version: str, environ: Mapping[str, str] = os.environ, platform: str = sys.platform) -> Path:
    """Houdini's user preferences directory for ``version`` (``X.Y``)."""
    override = environ.get("HOUDINI_USER_PREF_DIR", "").strip()
    if override:
        if "__HVER__" not in override:
            raise PackageError("HOUDINI_USER_PREF_DIR must contain __HVER__, as Houdini requires")
        return Path(override.replace("__HVER__", version)).expanduser()
    if platform == "darwin":
        return Path(environ.get("HOME") or Path.home()) / "Library" / "Preferences" / "houdini" / version
    if platform == "win32":
        home = environ.get("HOME")
        return (Path(home) if home else _documents_dir(environ)) / "houdini{}".format(version)
    return Path(environ.get("HOME") or Path.home()) / "houdini{}".format(version)


def package_document(root: Path) -> Dict[str, Any]:
    """The Houdini package that loads the adapter from ``root``."""
    return {
        "env": [
            {ROOT_ENV: root.as_posix()},
            {"PYTHONPATH": {"method": "prepend", "value": "$" + ROOT_ENV + "/lib"}},
        ],
        "hpath": "$" + ROOT_ENV + "/houdini",
    }


def _registered_root(path: Path) -> Optional[str]:
    """The package root a Meshy DCC package file points at, if it is one."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entries = document.get("env") if isinstance(document, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get(ROOT_ENV), str):
            return entry[ROOT_ENV]
    return None


def install(
    dcc_path: str, root: Path, environ: Mapping[str, str] = os.environ, platform: str = sys.platform
) -> Dict[str, Any]:
    """Write the package file for the Houdini at ``dcc_path``; replaces an older one."""
    for required in ("houdini", "lib/meshy_dcc_houdini"):
        if not (root / required).is_dir():
            raise PackageError("{} is not an extracted Meshy DCC Houdini package (no {}/)".format(root, required))
    version = houdini_version(dcc_path, environ)
    target = user_pref_dir(version, environ, platform) / "packages" / PACKAGE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name("." + PACKAGE_FILE + ".tmp")
    staging.write_text(json.dumps(package_document(root), indent=2) + "\n", encoding="utf-8")
    os.replace(str(staging), str(target))
    return {"status": "installed", "houdini_version": version, "package_file": str(target), "package_root": str(root)}


def uninstall(
    dcc_path: str, root: Path, environ: Mapping[str, str] = os.environ, platform: str = sys.platform
) -> Dict[str, Any]:
    """Delete the package file when it points at ``root``; leave anything else alone."""
    version = houdini_version(dcc_path, environ)
    target = user_pref_dir(version, environ, platform) / "packages" / PACKAGE_FILE
    result: Dict[str, Any] = {"houdini_version": version, "package_file": str(target)}
    if not target.exists():
        return dict(result, status="not_installed")
    if _registered_root(target) != root.as_posix():
        return dict(result, status="kept", reason="the package file belongs to another Meshy DCC Houdini package")
    target.unlink()
    return dict(result, status="removed")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-houdini", description=__doc__.splitlines()[0])
    parser.add_argument("verb", choices=("install", "uninstall"))
    parser.add_argument("--dcc-path", required=True, help="The Houdini executable this package is for")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    action = install if args.verb == "install" else uninstall
    try:
        result = action(args.dcc_path, package_root())
    except (PackageError, OSError) as exc:
        print("meshy-dcc-houdini {}: {}".format(args.verb, exc), file=sys.stderr)
        return 1
    print(
        json.dumps(result, sort_keys=True)
        if args.as_json
        else "{}: {}".format(result["status"], result["package_file"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
