"""Build the Meshy DCC FreeCAD package for one platform.

The service runs outside FreeCAD (it starts FreeCADCmd for every call), so the
package carries its own relocatable CPython (python-build-standalone) with
``meshy_dcc_core`` and this adapter installed::

    python/                      CPython and its site-packages
    bin/meshy-dcc-freecad        runs ``python -I -m meshy_dcc_freecad``
                                 (``.cmd`` in the Windows package)

``meshy-dcc install --dcc-type freecad --project <dir>`` extracts the zip and
runs ``bin/meshy-dcc-freecad install`` for the project.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel for the platform> \\
        --platform {macos-arm64,windows-x64} --output-dir dist [--python-archive <tar.gz>]

Both platforms build on any machine: the CPython is a pinned archive, and the
wheels are installed for the target platform without running its interpreter.
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
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
# CPython 3.11.15, python-build-standalone 20260504; digests from that release's SHA256SUMS.
PLATFORMS = {
    "macos-arm64": {
        "archive": "cpython-3.11.15%2B20260504-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "triple": "aarch64-apple-darwin",
        "site": "lib/python3.11/site-packages",
        "launcher": "bin/meshy-dcc-freecad",
        "script": '#!/bin/sh\nhere=$(cd "$(dirname "$0")" && pwd)\n'
        'exec "$here/../python/bin/python3.11" -I -m meshy_dcc_freecad "$@"\n',
    },
    "windows-x64": {
        "archive": "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "sha256": "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "triple": "x86_64-pc-windows-msvc",
        "site": "Lib/site-packages",
        "launcher": "bin/meshy-dcc-freecad.cmd",
        "script": '@echo off\r\n"%~dp0..\\python\\python.exe" -I -m meshy_dcc_freecad %*\r\n',
    },
}
# Not needed by the service: tests, GUI toolkits, headers, pip and build tools.
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
    "tk9*",
    "itcl*",
    "thread2*",
    "thread3*",
    "include",
    "pkgconfig",
    "libtcl*",
    "libtk*",
    "share",
    "Scripts",
    "libs",
    "pip",
    "pip-*",
    "EXTERNALLY-MANAGED",
    # bin/ scripts whose shebangs name the build prefix
    "2to3-3.11",
    "idle3.11",
    "pip3",
    "pip3.11",
    "pydoc3.11",
    "python3.11-config",
)


def adapter_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("version is missing from pyproject.toml")
    return match.group(1)


def build(platform: str, core_wheel: Path, python_archive: Path | None, output_dir: Path) -> Path:
    spec = PLATFORMS[platform]
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        if python_archive is None:
            python_archive = work / "python.tar.gz"
            urllib.request.urlretrieve(PBS + spec["archive"], python_archive)
        digest = hashlib.sha256(python_archive.read_bytes()).hexdigest()
        if digest != spec["sha256"]:
            raise SystemExit(f"{python_archive}: sha256 {digest}, expected {spec['sha256']}")
        with tarfile.open(python_archive) as archive:
            archive.extractall(work / "cpython", filter="data")

        stage = work / "package"
        shutil.copytree(
            work / "cpython" / "python", stage / "python", symlinks=True, ignore=EXCLUDED
        )
        site = stage / "python" / spec["site"]
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(site),
                "--python-platform",
                spec["triple"],
                "--python-version",
                "3.11",
                "--no-deps",
                str(core_wheel),
                str(ROOT),
            ],
            check=True,
        )
        # --target writes console-script launchers (pointing at this machine) and a lock file.
        for name in ("bin", "Scripts"):
            shutil.rmtree(site / name, ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)
        for cache in list(stage.rglob("__pycache__")):
            shutil.rmtree(cache)
        launcher = stage / spec["launcher"]
        launcher.parent.mkdir()
        launcher.write_bytes(spec["script"].encode("ascii"))
        launcher.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy-dcc-freecad-{platform}.zip"
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
            record.write_text(
                "".join(line for line in lines if not line.startswith(prefix)), encoding="utf-8"
            )


def write_zip(root: Path, archive: Path) -> None:
    """Zip ``root`` with sorted entries, fixed timestamps and Unix modes.

    Symlinks (CPython's ``python3`` and ``python`` aliases) are left out: the
    launcher names ``python3.11`` directly.
    """
    files = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            mode = 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--core-wheel", type=Path, required=True)
    parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    parser.add_argument(
        "--python-archive", type=Path, help="A downloaded copy of the pinned CPython"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build(args.platform, args.core_wheel, args.python_archive, args.output_dir)
    print(f"{archive}\nsha256 {hashlib.sha256(archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
