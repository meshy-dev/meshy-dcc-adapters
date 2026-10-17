"""Build the Meshy DCC Substance 3D Painter package for one platform.

Painter runs the adapter on its own embedded Python; the installer runs before
Painter is involved, so the package brings a relocatable CPython
(python-build-standalone) for it::

    plugin/python/                      this adapter and meshy_dcc_core; Painter's
                                        startup loader puts this folder on sys.path
    python/                             CPython 3.11 for the installer only
    bin/meshy-dcc-substance3d-painter   the installer (bin/...painter.cmd on Windows)

``meshy-dcc install --dcc-type substance3d_painter`` extracts the zip and runs
``bin/meshy-dcc-substance3d-painter install --yes --json``, which writes the
startup loader into the user's Painter profile.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel for the platform> \\
        --platform macos-arm64 --output-dir dist

Both platforms build on any machine: the CPython is a pinned
python-build-standalone download (its SHA-256 checked) and the Python packages
are installed for the target with ``uv pip install --python-platform``.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "meshy-dcc-substance3d-painter"
PYTHON_VERSION = "3.11"
PBS_RELEASE = "20260504"
PBS_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/"
# platform -> (python-build-standalone archive, its SHA-256 from the release's SHA256SUMS, uv target triple)
PLATFORMS = {
    "macos-arm64": (
        f"cpython-3.11.15+{PBS_RELEASE}-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "aarch64-apple-darwin",
    ),
    "windows-x64": (
        f"cpython-3.11.15+{PBS_RELEASE}-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "x86_64-pc-windows-msvc",
    ),
}
# Trimmed from the installer's runtime: tests, GUI toolkits, headers, launchers and the bundled
# pip and setuptools, none of which it loads.
EXCLUDED = shutil.ignore_patterns(
    "__pycache__",
    "site-packages",
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
    "tcl",
    "libs",
    "Scripts",
    "_tkinter*",
    "tcl86t.dll",
    "tk86t.dll",
)
POSIX_INSTALLER = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
unset PYTHONHOME
PYTHONPATH="$here/../plugin/python" exec "$here/../python/bin/python{version}" -s -m meshy_dcc_substance3d_painter.install_cli "$@"
"""
WINDOWS_INSTALLER = (
    "@echo off\r\n"
    "setlocal\r\n"
    'set "PYTHONHOME="\r\n'
    'set "PYTHONPATH=%~dp0..\\plugin\\python"\r\n'
    '"%~dp0..\\python\\python.exe" -s -m meshy_dcc_substance3d_painter.install_cli %*\r\n'
    "exit /b %ERRORLEVEL%\r\n"
)


def adapter_version() -> str:
    match = re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise RuntimeError("version is missing from pyproject.toml")
    return match.group(1)


def python_home(platform: str, cache: Path) -> Path:
    """The pinned CPython for ``platform``, downloaded once into ``cache`` and checked against its digest."""
    archive_name, digest, _ = PLATFORMS[platform]
    home = cache / archive_name.removesuffix(".tar.gz") / "python"
    if home.is_dir():
        return home
    archive = cache / archive_name
    if not archive.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PBS_URL + urllib.parse.quote(archive_name), archive)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != digest:
        archive.unlink()
        raise RuntimeError(f"{archive_name} has SHA-256 {actual}, expected {digest}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(home.parent, filter="data")
    return home


def build(core_wheel: Path, platform: str, output_dir: Path, cache: Path) -> Path:
    windows = platform == "windows-x64"
    triple = PLATFORMS[platform][2]
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        payload = stage / "plugin" / "python"
        # Symlinks are copied as files: core refuses packages that contain links.
        shutil.copytree(python_home(platform, cache), stage / "python", symlinks=False, ignore=EXCLUDED)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                PYTHON_VERSION,
                "--python-platform",
                triple,
                "--target",
                str(payload),
                "--no-deps",
                str(core_wheel),
                str(ROOT),
            ],
            check=True,
        )
        for leftover in ("bin", "Scripts"):
            shutil.rmtree(payload / leftover, ignore_errors=True)
        (payload / ".lock").unlink(missing_ok=True)
        strip_build_paths(payload)
        for cache_dir in list(stage.rglob("__pycache__")):
            shutil.rmtree(cache_dir)
        if not list((payload / "meshy_dcc_core").glob("_core*" + (".pyd" if windows else ".so"))):
            raise RuntimeError(f"{core_wheel.name} is not a {platform} meshy_dcc_core wheel")

        (stage / "bin").mkdir()
        if windows:
            installer = stage / "bin" / f"{NAME}.cmd"
            installer.write_bytes(WINDOWS_INSTALLER.encode("ascii"))
        else:
            installer = stage / "bin" / NAME
            installer.write_text(POSIX_INSTALLER.format(version=PYTHON_VERSION), encoding="utf-8")
        installer.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"{NAME}-{platform}.zip"
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
    parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--python-cache",
        type=Path,
        default=Path(tempfile.gettempdir()) / "meshy-dcc-python-build-standalone",
        help="Where the CPython downloads are kept",
    )
    args = parser.parse_args()
    print(f"adapter {adapter_version()}")
    archive = build(args.core_wheel, args.platform, args.output_dir, args.python_cache)
    print(f"{archive}\nsha256 {hashlib.sha256(archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
