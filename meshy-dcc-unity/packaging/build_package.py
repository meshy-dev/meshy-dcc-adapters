"""Build the Meshy DCC Unity package: the sidecar with its own Python.

Unity has no Python of its own, so the package carries a relocatable CPython
(python-build-standalone, the kind uv installs) with ``meshy_dcc_core``, this
adapter and ``websockets`` installed into it::

    python/                          CPython and its site-packages
    bin/meshy-dcc-unity-sidecar      runs ``python -m meshy_dcc_unity``
                                     (``meshy-dcc-unity-sidecar.cmd`` on Windows)

The Unity Editor package ships inside ``meshy_dcc_unity/unity_package``.
``meshy-dcc install --dcc-type unity --project <root>`` extracts the zip and
runs the bundled installer against the project.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> --output-dir dist

A Windows package builds from any host: pass the Windows core wheel and
``--python-home`` pointing at an extracted python-build-standalone
``x86_64-pc-windows-msvc`` install (the directory holding ``python.exe``).
The wheels are then installed for Windows with ``uv pip install --target``.
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
import tempfile
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
    "tcl",
    "tk8*",
    "itcl*",
    "thread2*",
    "include",
    "share",
    "EXTERNALLY-MANAGED",
)
SIDECAR_SCRIPT = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python{version}" -m meshy_dcc_unity "$@"
"""
# %~dp0 is this file's directory with a trailing backslash; %* passes the
# arguments as given.
SIDECAR_CMD = (
    "@echo off\r\n"
    '"%~dp0..\\python\\python.exe" -m meshy_dcc_unity %*\r\n'
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
    executable = Path(executable).resolve()
    # Windows keeps python.exe at the root of the install, POSIX in bin/.
    return executable.parent if executable.name.lower() == "python.exe" else executable.parents[1]


def is_windows_python(python_home: Path) -> bool:
    return (python_home / "python.exe").is_file()


def platform_tag(python_home: Path) -> str:
    if is_windows_python(python_home):
        return "windows_x86_64"
    machine = os.uname().machine if hasattr(os, "uname") else "x86_64"
    system = {"darwin": "macos", "linux": "linux"}.get(sys.platform, sys.platform)
    return f"{system}_{'arm64' if machine in {'arm64', 'aarch64'} else 'x86_64'}"


def build(core_wheel: Path, python_home: Path, output_dir: Path) -> Path:
    version = adapter_version()
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        shutil.copytree(python_home, stage / "python", symlinks=False, ignore=EXCLUDED)
        neutralize_python_prefix(stage / "python", python_home)
        packages = [str(core_wheel), str(ROOT), "websockets>=12,<18"]
        if is_windows_python(python_home):
            site = stage / "python" / "Lib" / "site-packages"
        else:
            site = stage / "python" / "lib" / f"python{PYTHON_VERSION}" / "site-packages"
        # By target, so no console script lands in python/bin with a shebang naming
        # this stage; the Windows interpreter cannot run here anyway.
        install = ["--target", str(site), "--python-version", PYTHON_VERSION]
        if is_windows_python(python_home):
            install += ["--python-platform", "x86_64-pc-windows-msvc"]
        subprocess.run(["uv", "pip", "install", *install, "--no-deps", *packages], check=True)
        # --target also writes console scripts that point at this machine's paths, and a lock file.
        shutil.rmtree(site / "bin", ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)
        (stage / "bin").mkdir()
        if is_windows_python(python_home):
            sidecar = stage / "bin" / "meshy-dcc-unity-sidecar.cmd"
            sidecar.write_bytes(SIDECAR_CMD.encode("ascii"))
        else:
            sidecar = stage / "bin" / "meshy-dcc-unity-sidecar"
            sidecar.write_text(SIDECAR_SCRIPT.format(version=PYTHON_VERSION), encoding="utf-8")
            sidecar.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy_dcc_unity_{platform_tag(python_home)}_v{version}.zip"
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
    parser.add_argument("--python-home", type=Path, help="Relocatable CPython root (default: uv's)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build(args.core_wheel, args.python_home or default_python_home(), args.output_dir)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
