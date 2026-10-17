"""Build the Meshy DCC Cinema 4D package: the adapter with its own Python.

The service runs outside Cinema 4D and starts the licensed ``c4dpy`` once per
operation, so the package carries a relocatable CPython (python-build-standalone,
pinned below) with ``meshy_dcc_core`` and this adapter in its site-packages::

    python/                    CPython 3.11 and its site-packages
    bin/meshy-dcc-c4d          runs ``python -I -m meshy_dcc_c4d`` (``.cmd`` on Windows)

``meshy-dcc install --dcc-type c4d --project <folder>`` extracts the zip and runs
``bin/meshy-dcc-c4d install --project <folder> --c4dpy <c4dpy> --yes --json``.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> \\
        --platform {macos-arm64,windows-x64} --output-dir <dir> [--python-archive <tar.gz>]

Both packages build on any machine: the wheels are installed for the target
platform with ``uv pip install --target``.
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
# python-build-standalone 20260504, CPython 3.11.15; the digests are the ones
# published in that release's SHA256SUMS.
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
PLATFORMS = {
    "macos-arm64": {
        "python_url": PBS
        + "cpython-3.11.15%2B20260504-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "python_sha256": "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "uv_platform": "aarch64-apple-darwin",
        "wheel_tag": "macosx_11_0_arm64",
        "site": "lib/python3.11/site-packages",
    },
    "windows-x64": {
        "python_url": PBS
        + "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "python_sha256": "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "uv_platform": "x86_64-pc-windows-msvc",
        "wheel_tag": "win_amd64",
        "site": "Lib/site-packages",
    },
}
# Left out of the runtime: tests, GUI toolkits, headers, pip and the embedding
# library (the macOS interpreter is linked statically).
EXCLUDED = shutil.ignore_patterns(
    "__pycache__",
    "test",
    "tests",
    "idlelib",
    "tkinter",
    "turtledemo",
    "ensurepip",
    "lib2to3",
    "pip",
    "pip-*.dist-info",
    "tcl",
    "tcl9*",
    "tk9*",
    "libtcl*",
    "libtk*",
    "itcl*",
    "thread3*",
    "_tkinter*",
    "libpython3*.dylib",
    "include",
    "libs",
    "share",
    "Scripts",
    "EXTERNALLY-MANAGED",
)
SCRIPT = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python3.11" -I -m meshy_dcc_c4d "$@"
"""
CMD = '@echo off\r\n"%~dp0..\\python\\python.exe" -I -m meshy_dcc_c4d %*\r\n'


def adapter_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("version is missing from pyproject.toml")


def build(core_wheel: Path, platform: str, output_dir: Path, python_archive: Path | None) -> Path:
    target = PLATFORMS[platform]
    if target["wheel_tag"] not in core_wheel.name:
        raise SystemExit(f"{core_wheel.name} is not a {target['wheel_tag']} wheel")
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        if python_archive is None:
            python_archive = work / "python.tar.gz"
            urllib.request.urlretrieve(target["python_url"], python_archive)
        digest = hashlib.sha256(python_archive.read_bytes()).hexdigest()
        if digest != target["python_sha256"]:
            raise SystemExit(f"{python_archive}: sha256 {digest}, expected {target['python_sha256']}")
        with tarfile.open(python_archive) as archive:
            archive.extractall(work / "cpython", filter="data")

        stage = work / "package"
        shutil.copytree(work / "cpython" / "python", stage / "python", ignore=EXCLUDED)
        bin_dir = stage / "python" / "bin"
        if bin_dir.is_dir():  # keep only the interpreter; the other scripts name the build prefix
            for item in bin_dir.iterdir():
                if item.name != f"python{PYTHON_VERSION}":
                    item.unlink()
        site = stage / "python" / target["site"]
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(site),
                "--python-platform",
                target["uv_platform"],
                "--python-version",
                PYTHON_VERSION,
                "--no-deps",
                str(core_wheel),
                str(ROOT),
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
        (stage / "bin").mkdir()
        if platform == "windows-x64":
            (stage / "bin" / "meshy-dcc-c4d.cmd").write_bytes(CMD.encode("ascii"))
        else:
            launcher = stage / "bin" / "meshy-dcc-c4d"
            launcher.write_text(SCRIPT, encoding="utf-8")
            launcher.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy-dcc-c4d-{platform}.zip"
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--python-archive", type=Path, help="A downloaded copy of the platform's CPython archive"
    )
    args = parser.parse_args()
    archive = build(args.core_wheel, args.platform, args.output_dir, args.python_archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
