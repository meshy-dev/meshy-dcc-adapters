"""Build the Meshy DCC Unreal package: the project plugin and its installer.

The plugin runs on the editor's own Python and carries its dependencies, so
it needs nothing installed into the engine; its C++ editor module ships as
source and the installer builds it per project. The installer runs before any
editor is involved, so the package brings a relocatable CPython
(python-build-standalone, the kind uv installs) for it::

    plugin/MeshyDccUnreal/           copied into <project>/Plugins/
      Source/                        the C++ editor module
      python/                        this adapter and meshy_dcc_core
    python/                          CPython for the installer
    bin/meshy-dcc-unreal             runs the installer from the plugin copy
                                     (bin/meshy-dcc-unreal.cmd on Windows)

``meshy-dcc install --dcc-type unreal --project <root>`` extracts the zip and
runs ``bin/meshy-dcc-unreal install <root> --yes --json``.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> --output-dir dist
    python packaging/build_package.py --platform windows-x86_64 \
        --core-wheel <meshy_dcc_core win_amd64 wheel> --output-dir dist

The Windows package is built on any machine: its CPython is the pinned
python-build-standalone build below, and the plugin's packages are installed
for Windows with ``uv pip install --python-platform``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "MeshyDccUnreal"
PYTHON_VERSION = "3.11"
# Trimmed from the installer's runtime: tests, GUI toolkits and build headers it never loads.
EXCLUDED = shutil.ignore_patterns(
    "__pycache__",
    "test",
    "tests",
    "idlelib",
    "tkinter",
    "turtledemo",
    "ensurepip",
    "lib2to3",
    "tcl8*",
    "tk8*",
    "itcl*",
    "thread2*",
    "include",
    "share",
    "EXTERNALLY-MANAGED",
    # Windows layout: Tcl/Tk, import libraries and pip launchers.
    "tcl",
    "libs",
    "Scripts",
    "_tkinter.pyd",
    "tcl86t.dll",
    "tk86t.dll",
)
# The C++ module ships as source; the installer builds it for each project with the local toolchain.
PLUGIN_EXCLUDED = shutil.ignore_patterns("__pycache__", "Binaries", "Intermediate", "*.pyc")
INSTALLER_SCRIPT = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
PYTHONPATH="$here/../plugin/{plugin}/python" exec "$here/../python/bin/python{version}" -m meshy_dcc_unreal.install_cli "$@"
"""
WINDOWS = "windows-x86_64"
# The python-build-standalone build of the CPython the macOS package bundles
# (uv's 3.11). The digest is pinned; it matches the release's SHA256SUMS.
PBS_RELEASE = "20260504"
PBS_WINDOWS = f"cpython-3.11.15+{PBS_RELEASE}-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
PBS_WINDOWS_SHA256 = "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe"
PBS_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/"
WINDOWS_INSTALLER_SCRIPT = (
    "@echo off\r\n"
    "setlocal\r\n"
    'set "PYTHONPATH=%~dp0..\\plugin\\{plugin}\\python"\r\n'
    '"%~dp0..\\python\\python.exe" -m meshy_dcc_unreal.install_cli %*\r\n'
    "exit /b %ERRORLEVEL%\r\n"
)


def adapter_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("version is missing from pyproject.toml")
    return match.group(1)


def default_python_home() -> Path:
    """The uv-managed CPython install for PYTHON_VERSION."""
    executable = subprocess.run(
        ["uv", "python", "find", "--managed-python", PYTHON_VERSION],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(executable).resolve().parents[1]


def windows_python_home(cache: Path) -> Path:
    """The pinned Windows CPython, downloaded once into ``cache`` and checked against its digest."""
    home = cache / PBS_WINDOWS.removesuffix(".tar.gz") / "python"
    if (home / "python.exe").is_file():
        return home
    archive = cache / PBS_WINDOWS
    if not archive.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PBS_URL + urllib.parse.quote(PBS_WINDOWS), archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != PBS_WINDOWS_SHA256:
        archive.unlink()
        raise RuntimeError(f"{PBS_WINDOWS} has SHA-256 {digest}, expected {PBS_WINDOWS_SHA256}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(home.parent, filter="data")
    return home


def platform_tag() -> str:
    machine = os.uname().machine if hasattr(os, "uname") else "x86_64"
    system = {"darwin": "macos", "linux": "linux"}.get(sys.platform, sys.platform)
    return f"{system}_{'arm64' if machine in {'arm64', 'aarch64'} else 'x86_64'}"


def build(core_wheel: Path, python_home: Path, output_dir: Path, target: str = "") -> Path:
    """Build for this machine, or for Windows when ``target`` is ``windows-x86_64``."""
    windows = target == WINDOWS
    version = adapter_version()
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        plugin = stage / "plugin" / PLUGIN_NAME
        shutil.copytree(ROOT / "unreal" / "plugin", plugin, ignore=PLUGIN_EXCLUDED)
        descriptor = json.loads((plugin / f"{PLUGIN_NAME}.uplugin").read_text(encoding="utf-8"))
        if descriptor.get("VersionName") != version:
            raise RuntimeError(f"{PLUGIN_NAME}.uplugin must name version {version}")

        shutil.copytree(python_home, stage / "python", symlinks=False, ignore=EXCLUDED)
        neutralize_python_prefix(stage / "python", python_home)
        if windows:
            # The stage's python.exe cannot run here; resolve for Windows instead.
            interpreter = [PYTHON_VERSION, "--python-platform", "x86_64-pc-windows-msvc"]
        else:
            interpreter = [str(stage / "python" / "bin" / f"python{PYTHON_VERSION}")]
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                *interpreter,
                "--target",
                str(plugin / "python"),
                "--no-deps",
                str(core_wheel),
                str(ROOT),
            ],
            check=True,
        )
        shutil.rmtree(plugin / "python" / "bin", ignore_errors=True)
        shutil.rmtree(plugin / "python" / "Scripts", ignore_errors=True)
        (plugin / "python" / ".lock").unlink(missing_ok=True)
        strip_build_paths(plugin / "python")
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)

        (stage / "bin").mkdir()
        if windows:
            installer = stage / "bin" / "meshy-dcc-unreal.cmd"
            installer.write_bytes(WINDOWS_INSTALLER_SCRIPT.format(plugin=PLUGIN_NAME).encode("ascii"))
        else:
            installer = stage / "bin" / "meshy-dcc-unreal"
            installer.write_text(INSTALLER_SCRIPT.format(plugin=PLUGIN_NAME, version=PYTHON_VERSION), encoding="utf-8")
        installer.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        tag = "windows_x86_64" if windows else platform_tag()
        archive = output_dir / f"meshy_dcc_unreal_{tag}_v{version}.zip"
        write_zip(stage, archive)
    return archive


def strip_build_paths(site: Path) -> None:
    """Drop ``direct_url.json``: it records the local paths the wheels were installed from."""
    for record in site.glob("*.dist-info/RECORD"):
        direct_url = record.with_name("direct_url.json")
        if direct_url.exists():
            direct_url.unlink()
            prefix = f"{record.parent.name}/direct_url.json,"
            lines = record.read_text(encoding="utf-8").splitlines(keepends=True)
            record.write_text("".join(line for line in lines if not line.startswith(prefix)), encoding="utf-8")


def neutralize_python_prefix(python: Path, python_home: Path) -> None:
    """Put back the neutral ``/install`` prefix that uv replaces with its own install path."""
    for sysconfig in python.glob("lib/python*/_sysconfigdata_*.py"):
        text = sysconfig.read_text(encoding="utf-8")
        sysconfig.write_text(text.replace(str(python_home), "/install"), encoding="utf-8")
    for dylib in python.glob("lib/libpython*.dylib"):
        # The interpreter is linked statically; only the library's own id names the path.
        subprocess.run(["install_name_tool", "-id", f"@rpath/{dylib.name}", str(dylib)], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(dylib)], check=True, capture_output=True)


def write_zip(root: Path, archive: Path) -> None:
    """Zip ``root`` with sorted entries, fixed timestamps and Unix modes."""
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            mode = 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--core-wheel", type=Path, required=True)
    parser.add_argument("--platform", choices=[WINDOWS], help="Build for another platform (default: this machine)")
    parser.add_argument("--python-home", type=Path, help="Relocatable CPython root (default: uv's, or the pinned Windows build)")
    parser.add_argument(
        "--python-cache",
        type=Path,
        default=Path(tempfile.gettempdir()) / "meshy-dcc-python-build-standalone",
        help="Where the Windows CPython download is kept",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if args.python_home:
        python_home = args.python_home
    elif args.platform == WINDOWS:
        python_home = windows_python_home(args.python_cache)
    else:
        python_home = default_python_home()
    archive = build(args.core_wheel, python_home, args.output_dir, args.platform or "")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
