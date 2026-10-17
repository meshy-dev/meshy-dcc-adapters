"""Build the Meshy DCC OpenSCAD package for one platform.

OpenSCAD has no Python of its own, so the package carries a relocatable
CPython (python-build-standalone) with ``meshy_dcc_core`` and this adapter::

    python/                               CPython and its site-packages
    bin/meshy-dcc-openscad-sidecar        runs ``python -I -m meshy_dcc_openscad``
                                          (``.cmd`` in the Windows package)

``meshy-dcc install --dcc-type openscad --project <dir>`` extracts the zip and
runs ``bin/meshy-dcc-openscad-sidecar install-project``.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> \\
        --platform {macos-arm64,windows-x64} --output-dir dist [--python-archive <tar.gz>]

Both platforms build on any machine: the CPython is a pinned archive and the
wheels are installed for the target platform without running its interpreter.
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
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
# CPython 3.11.15, python-build-standalone 20260504; digests from that release's SHA256SUMS.
PLATFORMS = {
    "macos-arm64": {
        "archive": "cpython-3.11.15%2B20260504-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "triple": "aarch64-apple-darwin",
        "site": "lib/python3.11/site-packages",
        "launcher": "bin/meshy-dcc-openscad-sidecar",
        "script": '#!/bin/sh\nhere=$(cd "$(dirname "$0")" && pwd)\n'
        'exec "$here/../python/bin/python3.11" -I -m meshy_dcc_openscad "$@"\n',
    },
    "windows-x64": {
        "archive": "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "sha256": "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "triple": "x86_64-pc-windows-msvc",
        "site": "Lib/site-packages",
        "launcher": "bin/meshy-dcc-openscad-sidecar.cmd",
        "script": '@echo off\r\n"%~dp0..\\python\\python.exe" -I -m meshy_dcc_openscad %*\r\n',
    },
}
# Not needed by the adapter: tests, GUI toolkits, headers, pip, setuptools, and
# the bin/ aliases (symlinks to python3.11, which a package zip cannot carry).
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
    "pkgconfig",
    "libtcl*",
    "libtk*",
    "setuptools*",
    "_distutils_hack",
    "distutils-precedence.pth",
    "share",
    "Scripts",
    "libs",
    "EXTERNALLY-MANAGED",
    "python3",
    "python",
    "python3-config",
    "python3.11-config",
    "idle3*",
    "pydoc3*",
    "2to3*",
    "pip",
    "pip-*",
    "pip3*",
)


def python_archive(platform: str, given: "Path | None", work: Path) -> Path:
    spec = PLATFORMS[platform]
    archive = given or work / "python.tar.gz"
    if given is None:
        urllib.request.urlretrieve(PBS + spec["archive"], archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        raise SystemExit(f"{archive}: sha256 {digest}, expected {spec['sha256']}")
    return archive


def build(core_wheel: Path, platform: str, output_dir: Path, archive: "Path | None") -> Path:
    spec = PLATFORMS[platform]
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        with tarfile.open(python_archive(platform, archive, work)) as bundle:
            bundle.extractall(work / "cpython", filter="data")
        stage = work / "package"
        shutil.copytree(work / "cpython" / "python", stage / "python", ignore=EXCLUDED)
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
        for leftover in ("bin", "Scripts"):
            shutil.rmtree(site / leftover, ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)
        for cache in list(stage.rglob("__pycache__")):
            shutil.rmtree(cache)
        launcher = stage / spec["launcher"]
        launcher.parent.mkdir()
        launcher.write_bytes(spec["script"].encode("ascii"))
        launcher.chmod(0o755)
        symlinks = [p for p in stage.rglob("*") if p.is_symlink()]
        if symlinks:
            raise SystemExit(f"the package cannot carry symlinks: {symlinks[:5]}")
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / f"meshy-dcc-openscad-{platform}.zip"
        write_zip(stage, zip_path)
    return zip_path


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
        "--python-archive", type=Path, help="a downloaded copy of the pinned CPython"
    )
    args = parser.parse_args()
    archive = build(args.core_wheel.resolve(), args.platform, args.output_dir, args.python_archive)
    print(f"{archive}\nsha256 {hashlib.sha256(archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
