"""Build the Meshy DCC Houdini package for one platform.

Houdini runs the adapter on its own Python; the package registers itself
through a Houdini package file, so nothing goes into the Houdini installation.
The registration runs before Houdini is involved, so the package brings a
relocatable CPython (python-build-standalone) for it::

    houdini/                        joins HOUDINI_PATH
      pythonX.Ylibs/uiready.py      starts the adapter when the UI is ready
      toolbar/meshy_dcc.shelf       Start / Stop / Server Info shelf tools
    lib/                            joins PYTHONPATH: this adapter and meshy_dcc_core
    python/                         CPython for the registration step only
    bin/meshy-dcc-houdini           registers or removes the package file
                                    (bin/meshy-dcc-houdini.cmd on Windows)

``meshy-dcc install --dcc-type houdini`` extracts the zip and runs
``bin/meshy-dcc-houdini install --dcc-path <houdini> --json``.

Usage::

    python packaging/build_package.py --platform macos-arm64 \
        --core-wheel <meshy_dcc_core macosx arm64 wheel> --output-dir dist
    python packaging/build_package.py --platform windows-x64 \
        --core-wheel <meshy_dcc_core win_amd64 wheel> --output-dir dist

Each run writes one ``meshy-dcc-houdini-<platform>.zip``. Both platforms
build on any machine: the CPython is a pinned python-build-standalone
download checked against its published digest, and ``lib/`` is installed for
the target with ``uv pip install --python-platform``.
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
HOUDINI_FILES = Path(__file__).resolve().parent / "houdini"
MIN_CORE_VERSION = "0.2.0"
MAX_CORE_VERSION_EXCLUSIVE = "0.3.0"
PYTHON_VERSION = "3.11"
# Houdini 20.5 and 21 ship Python 3.11; later releases may move up. Houdini only
# runs the uiready.py of its own Python version, so every candidate gets one.
STARTUP_PYTHON_MINORS = (11, 12, 13, 14)
# python-build-standalone 20260504, CPython 3.11.15; digests from that release's SHA256SUMS.
PBS_RELEASE = "20260504"
PBS_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/"
PLATFORMS = {
    "macos-arm64": {
        "archive": f"cpython-3.11.15+{PBS_RELEASE}-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "uv_platform": "aarch64-apple-darwin",
        "wheel_tag": re.compile(r"-macosx_\d+_\d+_(arm64|universal2)\.whl$"),
    },
    "windows-x64": {
        "archive": f"cpython-3.11.15+{PBS_RELEASE}-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "sha256": "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "uv_platform": "x86_64-pc-windows-msvc",
        "wheel_tag": re.compile(r"-win_amd64\.whl$"),
    },
}
# Trimmed from the registration runtime: tests, GUI toolkits, build headers and
# packages it never loads. The macOS interpreter is linked statically, so
# libpython is only for embedding.
EXCLUDED = shutil.ignore_patterns(
    "__pycache__",
    "site-packages",
    "libpython*",
    "libtcl*",
    "libtk*",
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
    # Windows layout: Tcl/Tk, import libraries and pip launchers.
    "tcl",
    "libs",
    "Scripts",
    "_tkinter.pyd",
    "tcl86t.dll",
    "tk86t.dll",
)
# -I keeps the script's own directory (the adapter package) off sys.path.
POSIX_LAUNCHER = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python3.11" -I "$here/../lib/meshy_dcc_houdini/houdini_package.py" "$@"
"""
WINDOWS_LAUNCHER = (
    "@echo off\r\n"
    "setlocal\r\n"
    '"%~dp0..\\python\\python.exe" -I "%~dp0..\\lib\\meshy_dcc_houdini\\houdini_package.py" %*\r\n'
    "exit /b %ERRORLEVEL%\r\n"
)


def adapter_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("version is missing from pyproject.toml")
    return match.group(1)


def _release(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def check_core_wheel(core_wheel: Path, platform: str) -> None:
    """The wheel must be meshy_dcc_core in range, built for ``platform``."""
    match = re.match(r"meshy_dcc_core-([^-]+)-", core_wheel.name)
    if match is None:
        raise SystemExit(f"{core_wheel.name} is not a meshy_dcc_core wheel")
    if not _release(MIN_CORE_VERSION) <= _release(match.group(1)) < _release(MAX_CORE_VERSION_EXCLUSIVE):
        raise SystemExit(f"{core_wheel.name}: need meshy_dcc_core>={MIN_CORE_VERSION},<{MAX_CORE_VERSION_EXCLUSIVE}")
    if not PLATFORMS[platform]["wheel_tag"].search(core_wheel.name):
        raise SystemExit(f"{core_wheel.name} is not built for {platform}")


def python_home(platform: str, cache: Path) -> Path:
    """The pinned CPython for ``platform``, downloaded once into ``cache`` and checked against its digest."""
    spec = PLATFORMS[platform]
    home = cache / spec["archive"].removesuffix(".tar.gz") / "python"
    if home.is_dir():
        return home
    archive = cache / spec["archive"]
    if not archive.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PBS_URL + urllib.parse.quote(spec["archive"]), archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        archive.unlink()
        raise SystemExit(f"{spec['archive']} has SHA-256 {digest}, expected {spec['sha256']}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(home.parent, filter="data")
    return home


def ignore_python_files(directory: str, names: list) -> set:
    """``EXCLUDED``, and in ``bin/`` everything but the interpreter the launcher runs.

    The other names there are symlinks or scripts; a zip of links would carry
    three copies of the interpreter.
    """
    ignored = set(EXCLUDED(directory, names))
    if Path(directory).name == "bin":
        ignored.update(name for name in names if name != f"python{PYTHON_VERSION}")
    return ignored


def stage_houdini_files(houdini: Path) -> None:
    """The HOUDINI_PATH entry: one uiready.py per candidate Python and the shelf."""
    hook = (HOUDINI_FILES / "uiready.py").read_bytes()
    for minor in STARTUP_PYTHON_MINORS:
        libs = houdini / f"python3.{minor}libs"
        libs.mkdir(parents=True)
        (libs / "uiready.py").write_bytes(hook)
    shutil.copytree(HOUDINI_FILES / "toolbar", houdini / "toolbar")


def build(core_wheel: Path, platform: str, python: Path, output_dir: Path) -> Path:
    check_core_wheel(core_wheel, platform)
    windows = platform == "windows-x64"
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        stage_houdini_files(stage / "houdini")
        lib = stage / "lib"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                PYTHON_VERSION,
                "--python-platform",
                PLATFORMS[platform]["uv_platform"],
                "--target",
                str(lib),
                "--no-deps",
                str(core_wheel),
                str(ROOT),
            ],
            check=True,
        )
        for leftover in ("bin", "Scripts"):
            shutil.rmtree(lib / leftover, ignore_errors=True)
        (lib / ".lock").unlink(missing_ok=True)
        strip_build_paths(lib)
        shutil.copytree(python, stage / "python", symlinks=False, ignore=ignore_python_files)
        for cache in list(stage.rglob("__pycache__")):
            shutil.rmtree(cache)

        (stage / "bin").mkdir()
        if windows:
            launcher = stage / "bin" / "meshy-dcc-houdini.cmd"
            launcher.write_bytes(WINDOWS_LAUNCHER.encode("ascii"))
        else:
            launcher = stage / "bin" / "meshy-dcc-houdini"
            launcher.write_text(POSIX_LAUNCHER, encoding="utf-8")
        launcher.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy-dcc-houdini-{platform}.zip"
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
    archive = build(args.core_wheel, args.platform, python_home(args.platform, args.python_cache), args.output_dir)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
