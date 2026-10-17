#!/usr/bin/env python3
"""Build one adapter's release zips under their CDN names.

  build_release.py <host> --core-wheel-dir <dir> --out <dir>

<dir> holds the meshy-dcc-core release wheels (macOS arm64 and win_amd64).
Writes meshy-dcc-<host>-macos-arm64.zip and meshy-dcc-<host>-windows-x64.zip
(only the platforms the host runs on) and SHA256SUMS to --out. The same
names go to the GitHub Release and the CDN.

An adapter's packaging/build_package.py takes --core-wheel, --platform
{macos-arm64,windows-x64} and --output-dir and writes one zip; the four
adapters that predate that interface are mapped below.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = ("macos-arm64", "windows-x64")
ONLY = {"3dsmax": ("windows-x64",)}
WHEEL_GLOB = {"macos-arm64": "meshy_dcc_core-*-macosx_*_arm64.whl", "windows-x64": "meshy_dcc_core-*-win_amd64.whl"}

# The Unity build takes a Windows CPython root rather than downloading one;
# same build as the Godot and Unreal packages pin.
WINDOWS_PYTHON_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
    "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
)
WINDOWS_PYTHON_SHA256 = "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe"


def windows_python(tmp: Path) -> Path:
    archive = tmp / "cpython-windows.tar.gz"
    urllib.request.urlretrieve(WINDOWS_PYTHON_URL, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != WINDOWS_PYTHON_SHA256:
        sys.exit(f"{archive}: sha256 {digest}, expected {WINDOWS_PYTHON_SHA256}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(tmp, filter="data")
    return tmp / "python"


def build_args(host: str, platform: str, wheel: Path, out: Path, tmp: Path) -> list[str]:
    windows = platform == "windows-x64"
    common = ["--core-wheel", str(wheel), "--output-dir", str(out)]
    if host == "blender":
        return ["packaging/assemble_zip.py", "--platform", "win64" if windows else "macos", *common]
    if host == "unity":
        return ["packaging/build_package.py", *common, *(["--python-home", str(windows_python(tmp))] if windows else [])]
    if host == "godot":
        return ["packaging/build_package.py", *common, *(["--target", "windows-x86_64"] if windows else [])]
    if host == "unreal":
        return ["packaging/build_package.py", *common, *(["--platform", "windows-x86_64"] if windows else [])]
    return ["packaging/build_package.py", *common, "--platform", platform]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("host")
    parser.add_argument("--core-wheel-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    adapter = ROOT / f"meshy-dcc-{args.host}"
    if not adapter.is_dir():
        sys.exit(f"no adapter directory {adapter.name}")
    args.out.mkdir(parents=True, exist_ok=True)

    sums = []
    for platform in ONLY.get(args.host, PLATFORMS):
        wheels = sorted(args.core_wheel_dir.glob(WHEEL_GLOB[platform]))
        if len(wheels) != 1:
            sys.exit(f"expected one {WHEEL_GLOB[platform]} in {args.core_wheel_dir}, found {len(wheels)}")
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            staged = tmp / "out"
            staged.mkdir()
            command = build_args(args.host, platform, wheels[0].resolve(), staged, tmp)
            subprocess.run(["uv", "run", "--python", "3.11", "--no-project", "python", *command], cwd=adapter, check=True)
            built = list(staged.glob("*.zip"))
            if len(built) != 1:
                sys.exit(f"{args.host} {platform}: expected one zip, got {[p.name for p in built]}")
            target = args.out / f"meshy-dcc-{args.host}-{platform}.zip"
            shutil.move(built[0], target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        sums.append(f"{digest}  {target.name}\n")
        print(f"{target}\nsha256 {digest}")
    (args.out / "SHA256SUMS").write_text("".join(sums))


if __name__ == "__main__":
    main()
