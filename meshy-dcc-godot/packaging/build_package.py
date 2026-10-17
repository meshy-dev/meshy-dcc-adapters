"""Build the Meshy DCC Godot package: the sidecar with its own Python.

Godot has no Python of its own, so the package carries a relocatable CPython
(python-build-standalone, the kind uv installs) with ``meshy_dcc_core``, this
adapter and ``websockets`` installed into it::

    python/                          CPython and its site-packages
    bin/meshy-dcc-godot-sidecar      runs ``python -m meshy_dcc_godot``
                                     (``.cmd`` in the Windows package)

The EditorPlugin ships inside ``meshy_dcc_godot/godot_addon``.
``meshy-dcc install --dcc-type godot --project <root>`` extracts the zip and
runs the bundled installer against the project.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> --output-dir dist
    python packaging/build_package.py --target windows-x86_64 \\
        --core-wheel <win_amd64 meshy_dcc_core wheel> --output-dir dist [--python-archive <tar.gz>]

The Windows package is built on any machine: its CPython is the pinned
python-build-standalone archive below, and the wheels are installed for Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.11"
# Trimmed from the runtime: tests, GUI toolkits and build headers the sidecar never loads.
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
)
# python-build-standalone 20260504, CPython 3.11.15 (the version uv installs on
# macOS); the digest is the one published in that release's SHA256SUMS.
WINDOWS_PYTHON_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
    "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
)
WINDOWS_PYTHON_SHA256 = "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe"
# Not needed beside the sidecar on Windows: pip's launchers, Tcl/Tk, import libraries.
WINDOWS_EXCLUDED = shutil.ignore_patterns("Scripts", "tcl", "libs")
SIDECAR_CMD = '@echo off\r\n"%~dp0..\\python\\python.exe" -m meshy_dcc_godot %*\r\n'
SIDECAR_SCRIPT = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python{version}" -m meshy_dcc_godot "$@"
"""


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


def platform_tag() -> str:
    machine = os.uname().machine if hasattr(os, "uname") else "x86_64"
    system = {"darwin": "macos", "linux": "linux"}.get(sys.platform, sys.platform)
    return f"{system}_{'arm64' if machine in {'arm64', 'aarch64'} else 'x86_64'}"


def build(core_wheel: Path, python_home: Path, output_dir: Path) -> Path:
    version = adapter_version()
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        shutil.copytree(python_home, stage / "python", symlinks=False, ignore=EXCLUDED)
        neutralize_python_prefix(stage / "python", python_home)
        site = stage / "python" / "lib" / f"python{PYTHON_VERSION}" / "site-packages"
        # By target, so no console script lands in python/bin with a shebang naming this stage.
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(site),
                "--python-version",
                PYTHON_VERSION,
                "--no-deps",
                str(core_wheel),
                str(ROOT),
                "websockets>=12,<18",
            ],
            check=True,
        )
        shutil.rmtree(site / "bin", ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)
        sidecar = stage / "bin" / "meshy-dcc-godot-sidecar"
        sidecar.parent.mkdir()
        sidecar.write_text(SIDECAR_SCRIPT.format(version=PYTHON_VERSION), encoding="utf-8")
        sidecar.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy_dcc_godot_{platform_tag()}_v{version}.zip"
        write_zip(stage, archive)
    return archive


def build_windows(core_wheel: Path, python_archive: Path | None, output_dir: Path) -> Path:
    """The Windows x86_64 package, built from the pinned CPython archive."""
    version = adapter_version()
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        if python_archive is None:
            python_archive = work / "python.tar.gz"
            urllib.request.urlretrieve(WINDOWS_PYTHON_URL, python_archive)
        digest = hashlib.sha256(python_archive.read_bytes()).hexdigest()
        if digest != WINDOWS_PYTHON_SHA256:
            raise SystemExit(f"{python_archive}: sha256 {digest}, expected {WINDOWS_PYTHON_SHA256}")
        with tarfile.open(python_archive) as archive:
            archive.extractall(work / "cpython", filter="data")

        stage = work / "package"
        excluded = [EXCLUDED, WINDOWS_EXCLUDED]
        shutil.copytree(
            work / "cpython" / "python",
            stage / "python",
            ignore=lambda folder, names: set().union(*(rule(folder, names) for rule in excluded)),
        )
        site = stage / "python" / "Lib" / "site-packages"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(site),
                "--python-platform",
                "x86_64-pc-windows-msvc",
                "--python-version",
                PYTHON_VERSION,
                "--no-deps",
                str(core_wheel),
                str(ROOT),
                "websockets>=12,<18",
            ],
            check=True,
        )
        # --target writes console-script launchers (pointing at this machine) and a lock file.
        shutil.rmtree(site / "bin", ignore_errors=True)
        shutil.rmtree(site / "Scripts", ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)
        sidecar = stage / "bin" / "meshy-dcc-godot-sidecar.cmd"
        sidecar.parent.mkdir()
        sidecar.write_bytes(SIDECAR_CMD.encode("ascii"))

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy_dcc_godot_windows_x86_64_v{version}.zip"
        write_zip(stage, archive)
    return archive


def strip_build_paths(site: Path) -> None:
    """Drop what records the build machine: ``direct_url.json`` (local wheel paths),
    uv's ``uv_cache.json`` (a timestamp) and the RECORD lines of the removed console
    scripts (their shebangs name the build interpreter)."""
    for record in site.glob("*.dist-info/RECORD"):
        dropped = []
        for name in ("direct_url.json", "uv_cache.json"):
            path = record.with_name(name)
            if path.exists():
                path.unlink()
                dropped.append(f"{record.parent.name}/{name},")
        lines = record.read_text(encoding="utf-8").splitlines(keepends=True)
        drop = (*dropped, "bin/", "Scripts/", "../")
        record.write_text("".join(x for x in lines if not x.startswith(drop)), encoding="utf-8")


def neutralize_python_prefix(python: Path, python_home: Path) -> None:
    """Put back the neutral ``/install`` prefix that uv replaces with its own install path."""
    for sysconfig in python.glob("lib/python*/_sysconfigdata_*.py"):
        text = sysconfig.read_text(encoding="utf-8")
        sysconfig.write_text(text.replace(str(python_home), "/install"), encoding="utf-8")
    for dylib in python.glob("lib/libpython*.dylib"):
        # The interpreter is linked statically; only the library's own id names the path.
        # A pristine build still names /install: keep its bytes as published.
        if str(python_home).encode() not in dylib.read_bytes():
            continue
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
    parser.add_argument("--target", choices=["host", "windows-x86_64"], default="host")
    parser.add_argument("--python-home", type=Path, help="Relocatable CPython root (default: uv's)")
    parser.add_argument(
        "--python-archive", type=Path, help="Windows: a downloaded copy of WINDOWS_PYTHON_URL"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if args.target == "windows-x86_64":
        archive = build_windows(args.core_wheel, args.python_archive, args.output_dir)
    else:
        archive = build(args.core_wheel, args.python_home or default_python_home(), args.output_dir)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
