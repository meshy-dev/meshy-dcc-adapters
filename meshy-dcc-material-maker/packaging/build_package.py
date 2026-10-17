"""Build the Meshy DCC Material Maker package: the sidecar with its own Python.

Material Maker has no Python, so the package carries a relocatable CPython
3.11.15 (python-build-standalone 20260504, digest pinned below) with
``meshy_dcc_core`` and this adapter installed into it::

    python/                                   CPython and its site-packages
    bin/meshy-dcc-material-maker-sidecar      runs ``python -I -m meshy_dcc_material_maker``
                                              (``.cmd`` in the Windows package)

``meshy-dcc install --dcc-type material-maker --project <folder>`` extracts the
zip and runs ``install-project`` from it against the folder.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> \\
        --platform {macos-arm64,windows-x64} --output-dir dist [--python-archive <tar.gz>]

Either package builds on any machine: the CPython comes from the pinned
archive and the wheels are installed for the target platform. The core wheel
must be the target platform's.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.11"
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
# platform: (CPython archive, its digest from the release's SHA256SUMS, uv platform)
PLATFORMS = {
    "macos-arm64": (
        PBS + "cpython-3.11.15%2B20260504-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "aarch64-apple-darwin",
    ),
    "windows-x64": (
        PBS + "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "x86_64-pc-windows-msvc",
    ),
}
# Trimmed from the runtime: tests, GUI toolkits, pip's launchers and build headers.
EXCLUDED = shutil.ignore_patterns(
    "__pycache__",
    "test",
    "tests",
    "idlelib",
    "tkinter",
    "turtledemo",
    "ensurepip",
    "lib2to3",
    "tcl*",
    "tk8*",
    "itcl*",
    "thread2*",
    "include",
    "share",
    "Scripts",
    "libs",
    "EXTERNALLY-MANAGED",
)
SIDECAR_SCRIPT = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python3.11" -I -m meshy_dcc_material_maker "$@"
"""
SIDECAR_CMD = '@echo off\r\n"%~dp0..\\python\\python.exe" -I -m meshy_dcc_material_maker %*\r\n'


def build(core_wheel: Path, platform: str, python_archive: Path | None, output_dir: Path) -> Path:
    url, digest, uv_platform = PLATFORMS[platform]
    windows = platform.startswith("windows")
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        if python_archive is None:
            python_archive = work / "python.tar.gz"
            urllib.request.urlretrieve(url, python_archive)
        actual = hashlib.sha256(python_archive.read_bytes()).hexdigest()
        if actual != digest:
            raise SystemExit(f"{python_archive}: sha256 {actual}, expected {digest}")
        with tarfile.open(python_archive) as archive:
            archive.extractall(work / "cpython", filter="data")

        stage = work / "package"
        shutil.copytree(work / "cpython" / "python", stage / "python", ignore=EXCLUDED, symlinks=True)
        site = (
            stage / "python" / "Lib" / "site-packages"
            if windows
            else stage / "python" / "lib" / f"python{PYTHON_VERSION}" / "site-packages"
        )
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(site),
                "--python-platform",
                uv_platform,
                "--python-version",
                PYTHON_VERSION,
                "--no-deps",
                str(core_wheel),
                str(ROOT),
            ],
            check=True,
        )
        # --target writes console-script launchers (pointing at this machine),
        # a lock file and direct_url.json records of the local source paths.
        for launchers in ("bin", "Scripts"):
            shutil.rmtree(site / launchers, ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)
        (stage / "bin").mkdir()
        if windows:
            (stage / "bin" / "meshy-dcc-material-maker-sidecar.cmd").write_bytes(SIDECAR_CMD.encode("ascii"))
        else:
            sidecar = stage / "bin" / "meshy-dcc-material-maker-sidecar"
            sidecar.write_text(SIDECAR_SCRIPT, encoding="utf-8")
            sidecar.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy-dcc-material-maker-{platform}.zip"
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


def write_zip(root: Path, archive: Path) -> None:
    """Zip ``root`` with sorted entries, fixed timestamps and Unix modes.

    Symbolic links (``python3`` -> ``python3.11``) are stored as copies:
    ``meshy-dcc install`` refuses packages that contain links.
    """
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
    parser.add_argument("--python-archive", type=Path, help="A downloaded copy of the pinned CPython")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build(args.core_wheel, args.platform, args.python_archive, args.output_dir)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
