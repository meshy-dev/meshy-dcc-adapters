"""Build the Meshy DCC 3ds Max package: the adapter, meshy_dcc_core and an installer.

3ds Max runs only on Windows, so there is one package, ``windows-x64``::

    payload/                     meshy_dcc_3dsmax and meshy_dcc_core (win_amd64, abi3),
                                 loaded by 3ds Max's own Python from this folder
    python/                      CPython 3.11 that runs the installer
    bin/meshy-dcc-3dsmax.cmd     the installer (payload/meshy_dcc_3dsmax/host_install.py)

``meshy-dcc install --dcc-type 3dsmax`` extracts the zip and runs
``bin/meshy-dcc-3dsmax.cmd install --dcc-path <3dsmax.exe> --yes --json``,
which writes the startup script that loads ``payload/`` into 3ds Max.

Usage (on any machine)::

    python packaging/build_package.py --core-wheel <meshy_dcc_core win_amd64 wheel> \\
        --platform windows-x64 --output-dir dist

The installer's CPython is the pinned python-build-standalone build below; the
payload's packages are installed for Windows with ``uv pip install
--python-platform``.
"""

from __future__ import annotations

import argparse
import hashlib
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
PLATFORM = "windows-x64"
PACKAGE_NAME = "meshy-dcc-3dsmax-windows-x64.zip"
# Same CPython as the other Meshy DCC Windows packages; the digest matches the release's SHA256SUMS.
PBS_RELEASE = "20260504"
PBS_WINDOWS = f"cpython-3.11.15+{PBS_RELEASE}-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
PBS_WINDOWS_SHA256 = "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe"
PBS_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/"
# Trimmed from the installer's runtime, which needs only the standard library:
# tests, Tcl/Tk, headers, import libraries, pip and setuptools.
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
    "include",
    "share",
    "tcl",
    "libs",
    "Scripts",
    "_tkinter.pyd",
    "tcl86t.dll",
    "tk86t.dll",
)
# -I: isolated, so neither PYTHONPATH nor the script's folder can shadow the standard library.
INSTALLER_SCRIPT = (
    "@echo off\r\n"
    "setlocal\r\n"
    '"%~dp0..\\python\\python.exe" -I "%~dp0..\\payload\\meshy_dcc_3dsmax\\host_install.py" %*\r\n'
    "exit /b %ERRORLEVEL%\r\n"
)


def windows_python_home(cache: Path) -> Path:
    """The pinned Windows CPython, downloaded once into ``cache`` and checked against its digest."""
    home = cache / PBS_WINDOWS.removesuffix(".tar.gz") / "python"
    if (home / "python.exe").is_file():
        return home
    archive = cache / PBS_WINDOWS
    if not archive.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PBS_URL + urllib.parse.quote(PBS_WINDOWS), archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != PBS_WINDOWS_SHA256:
        archive.unlink()
        raise RuntimeError(f"{PBS_WINDOWS} has SHA-256 {digest}, expected {PBS_WINDOWS_SHA256}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(home.parent, filter="data")
    return home


def build(core_wheel: Path, python_home: Path, output_dir: Path) -> Path:
    if not core_wheel.name.endswith("win_amd64.whl"):
        raise RuntimeError(f"3ds Max needs the win_amd64 meshy_dcc_core wheel, got {core_wheel.name}")
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        payload = stage / "payload"
        shutil.copytree(python_home, stage / "python", symlinks=False, ignore=EXCLUDED)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                "3.11",
                "--python-platform",
                "x86_64-pc-windows-msvc",
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
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)
        for name in ("meshy_dcc_3dsmax/host_install.py", "meshy_dcc_core/_core.pyd"):
            if not (payload / name).is_file():
                raise RuntimeError(f"payload is missing {name}")

        (stage / "bin").mkdir()
        (stage / "bin" / "meshy-dcc-3dsmax.cmd").write_bytes(INSTALLER_SCRIPT.encode("ascii"))

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / PACKAGE_NAME
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
    parser.add_argument(
        "--platform", default=PLATFORM, choices=[PLATFORM], help="3ds Max is Windows-only: windows-x64"
    )
    parser.add_argument("--python-home", type=Path, help="Windows CPython root (default: the pinned build)")
    parser.add_argument(
        "--python-cache",
        type=Path,
        default=Path(tempfile.gettempdir()) / "meshy-dcc-python-build-standalone",
        help="Where the Windows CPython download is kept",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    python_home = args.python_home or windows_python_home(args.python_cache)
    archive = build(args.core_wheel, python_home, args.output_dir)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
