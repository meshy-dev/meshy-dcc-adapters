"""Build the Meshy DCC Roblox Studio package for one platform.

Roblox Studio has no Python, so the package carries its own relocatable
CPython (python-build-standalone, pinned below by SHA-256) with
``meshy_dcc_core``, this adapter, ``websockets`` and ``pillow`` installed::

    python/        CPython; run ``python -m meshy_dcc_roblox <verb>``

``meshy-dcc install --dcc-type roblox --project <dir>`` extracts the zip and
runs ``python -m meshy_dcc_roblox install --project <dir>`` with that Python.
Both platforms build on any machine; wheels are picked for the target.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel for the platform> \\
        --platform macos-arm64|windows-x64 --output-dir dist [--python-archive <tar.gz>]
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
PYTHON_VERSION = "3.11"
RELEASE = "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
# python-build-standalone 20260504, CPython 3.11.15; digests from that release's SHA256SUMS.
PLATFORMS = {
    "macos-arm64": {
        "archive": "cpython-3.11.15%2B20260504-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "triple": "aarch64-apple-darwin",
        "site": f"lib/python{PYTHON_VERSION}/site-packages",
    },
    "windows-x64": {
        "archive": "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "sha256": "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "triple": "x86_64-pc-windows-msvc",
        "site": "Lib/site-packages",
    },
}
DEPENDENCIES = ["websockets==17.2", "pillow==13.0.0"]
# Parts of the runtime the sidecar never loads: tests, GUI toolkits, headers,
# pip's launchers and the bin/ symlinks (a package zip may not hold symlinks).
EXCLUDED = shutil.ignore_patterns(
    "__pycache__", "test", "tests", "idlelib", "tkinter", "turtledemo", "ensurepip", "lib2to3",
    "tcl*", "tk8*", "itcl*", "thread2*", "include", "share", "pkgconfig", "Scripts", "libs",
    "EXTERNALLY-MANAGED",
)


def adapter_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("version is missing from pyproject.toml")
    return match.group(1)


def build(core_wheel: Path, platform: str, output_dir: Path, python_archive: Path | None) -> Path:
    spec = PLATFORMS[platform]
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        if python_archive is None:
            python_archive = work / "python.tar.gz"
            urllib.request.urlretrieve(RELEASE + spec["archive"], python_archive)
        digest = hashlib.sha256(python_archive.read_bytes()).hexdigest()
        if digest != spec["sha256"]:
            raise SystemExit(f"{python_archive}: sha256 {digest}, expected {spec['sha256']}")
        with tarfile.open(python_archive) as archive:
            archive.extractall(work / "cpython", filter="data")

        stage = work / "package"
        shutil.copytree(work / "cpython" / "python", stage / "python", symlinks=True, ignore=EXCLUDED)
        bin_dir = stage / "python" / "bin"
        if bin_dir.is_dir():  # keep only the interpreter itself
            for entry in bin_dir.iterdir():
                if entry.name != f"python{PYTHON_VERSION}":
                    entry.unlink()
        links = [path for path in stage.rglob("*") if path.is_symlink()]
        if links:
            raise SystemExit(f"symlinks left in the runtime: {links}")
        site = stage / "python" / spec["site"]
        subprocess.run(
            [
                "uv", "pip", "install", "--target", str(site),
                "--python-platform", spec["triple"], "--python-version", PYTHON_VERSION,
                "--no-deps",
                str(core_wheel), str(ROOT), *DEPENDENCIES,
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

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy-dcc-roblox-{platform}.zip"
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
    parser.add_argument("--python-archive", type=Path, help="A downloaded copy of the pinned CPython archive")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build(args.core_wheel, args.platform, args.output_dir, args.python_archive)
    print(f"{archive}\nsha256 {hashlib.sha256(archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
