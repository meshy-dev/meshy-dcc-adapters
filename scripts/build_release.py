#!/usr/bin/env python3
"""Build one adapter's release zips under their CDN names.

  build_release.py <host> --core-wheel-dir <dir> --out <dir>

<dir> holds the meshy-dcc-core release wheels (macOS arm64 and win_amd64; only
the one --platform needs when it is given).
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
import os
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

# Unity on both platforms, and Godot and Unreal on macOS, default to uv's
# CPython, which varies with the uv version; hand them the build the other
# packages pin.
PYTHON_URL = "https://github.com/astral-sh/python-build-standalone/releases/download/20260504/"
PYTHONS = {
    "macos-arm64": (
        "cpython-3.11.15%2B20260504-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
    ),
    "windows-x64": (
        "cpython-3.11.15%2B20260504-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
    ),
}
# Packages resolved from PyPI (build backends, websockets) as of this date, so
# a tag rebuilds byte for byte; move it forward to take newer releases.
EXCLUDE_NEWER = "2026-10-17T00:00:00Z"


def pinned_python(platform: str, tmp: Path) -> Path:
    name, sha256 = PYTHONS[platform]
    archive = tmp / "cpython.tar.gz"
    urllib.request.urlretrieve(PYTHON_URL + name, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != sha256:
        sys.exit(f"{archive}: sha256 {digest}, expected {sha256}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(tmp, filter="data")
    return tmp / "python"


def build_args(host: str, platform: str, wheel: Path, out: Path, tmp: Path) -> list[str]:
    windows = platform == "windows-x64"
    common = ["--core-wheel", str(wheel), "--output-dir", str(out)]
    if host == "blender":
        return ["packaging/assemble_zip.py", "--platform", "win64" if windows else "macos", *common]
    if host == "unity":
        return ["packaging/build_package.py", *common, "--python-home", str(pinned_python(platform, tmp))]
    if host == "godot":
        target = ["--target", "windows-x86_64"] if windows else ["--python-home", str(pinned_python(platform, tmp))]
        return ["packaging/build_package.py", *common, *target]
    if host == "unreal":
        target = ["--platform", "windows-x86_64"] if windows else ["--python-home", str(pinned_python(platform, tmp))]
        return ["packaging/build_package.py", *common, *target]
    return ["packaging/build_package.py", *common, "--platform", platform]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("host")
    parser.add_argument("--core-wheel-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--platform", choices=PLATFORMS, help="Build only this platform (default: all the host runs on)")
    args = parser.parse_args()

    adapter = ROOT / f"meshy-dcc-{args.host}"
    if not adapter.is_dir():
        sys.exit(f"no adapter directory {adapter.name}")
    args.out.mkdir(parents=True, exist_ok=True)

    sums = []
    platforms = ONLY.get(args.host, PLATFORMS)
    if args.platform:
        if args.platform not in platforms:
            sys.exit(f"{args.host} has no {args.platform} build")
        platforms = (args.platform,)
    for platform in platforms:
        wheels = sorted(args.core_wheel_dir.glob(WHEEL_GLOB[platform]))
        if len(wheels) != 1:
            sys.exit(f"expected one {WHEEL_GLOB[platform]} in {args.core_wheel_dir}, found {len(wheels)}")
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            staged = tmp / "out"
            staged.mkdir()
            command = build_args(args.host, platform, wheels[0].resolve(), staged, tmp)
            subprocess.run(
                ["uv", "run", "--python", "3.11", "--no-project", "python", *command],
                cwd=adapter,
                env={**os.environ, "UV_EXCLUDE_NEWER": EXCLUDE_NEWER},
                check=True,
            )
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
