"""Build the Meshy DCC Maya package: a Maya module and its installer.

Maya brings its own Python, so the module carries this adapter and
``meshy_dcc_core`` and runs on it; nothing is installed into Maya. The
installer runs before Maya is involved, so the package brings a relocatable
CPython (python-build-standalone, pinned below) for it::

    module/                        the Maya module (the .mod file points here)
      plug-ins/meshy_dcc_maya_plugin.py
      scripts/userSetup.py         loads the plug-in when Maya starts
      python/                      this adapter, meshy_dcc_core and packaging
    python/                        CPython for the installer
    bin/meshy-dcc-maya             runs module_install.py with that CPython
                                   (bin/meshy-dcc-maya.cmd on Windows)

``meshy-dcc install --dcc-type maya`` extracts the zip and runs
``bin/meshy-dcc-maya install --json``, which writes ``meshy_dcc_maya.mod``
into the user's Maya modules folder.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> \\
        --platform macos-arm64 --output-dir dist

Both platforms build on any machine: the CPython is downloaded and checked
against the digest below, and the module's packages are installed for the
target with ``uv pip install --python-platform``.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.11"
PBS_RELEASE = "20260504"
PBS_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/"
# Digests from the release's SHA256SUMS.
PLATFORMS = {
    "macos-arm64": {
        "pbs": f"cpython-3.11.15+{PBS_RELEASE}-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": "505975e41e03ecc92ec5c666420481a20e7d4ade2d004b0f0a15fa08343910e3",
        "uv_platform": "aarch64-apple-darwin",
        "wheel_tag": "macosx_11_0_arm64",
    },
    "windows-x64": {
        "pbs": f"cpython-3.11.15+{PBS_RELEASE}-x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
        "sha256": "3faa1bec91efb6c3d98dd9a1dfae6ec4a40a855a8bb793ac2a2f2b1689816cfe",
        "uv_platform": "x86_64-pc-windows-msvc",
        "wheel_tag": "win_amd64",
    },
}
# Trimmed from the installer's runtime: it only needs the interpreter and the
# standard library, not pip, tests, GUI toolkits, headers or the shared libpython
# (the macOS interpreter is linked statically).
_TRIMMED = shutil.ignore_patterns(
    "__pycache__",
    "test",
    "tests",
    "site-packages",
    "idlelib",
    "tkinter",
    "turtledemo",
    "ensurepip",
    "lib2to3",
    "pydoc_data",
    "tcl",
    "tcl[0-9]*",
    "tk[0-9]*",
    "itcl[0-9]*",
    "thread[0-9]*",
    "libtcl*",
    "include",
    "share",
    "pkgconfig",
    "libpython*.dylib",
    "EXTERNALLY-MANAGED",
    # Windows layout: Tcl/Tk, import libraries and pip launchers.
    "libs",
    "Scripts",
    "_tkinter.pyd",
    "pythonw.exe",
)


def _trimmed(directory: str, names: list) -> set:
    """``_TRIMMED`` plus symlinks, and every ``bin/`` entry but the interpreter."""
    skipped = set(_TRIMMED(directory, names))
    skipped.update(name for name in names if Path(directory, name).is_symlink())
    if Path(directory).name == "bin":
        skipped.update(name for name in names if name != f"python{PYTHON_VERSION}")
    return skipped


INSTALLER = "module/python/meshy_dcc_maya/module_install.py"
POSIX_LAUNCHER = f"""#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python{PYTHON_VERSION}" -I "$here/../{INSTALLER}" "$@"
"""
WINDOWS_LAUNCHER = (
    "@echo off\r\n"
    f'"%~dp0..\\python\\python.exe" -I "%~dp0..\\{INSTALLER.replace("/", chr(92))}" %*\r\n'
    "exit /b %ERRORLEVEL%\r\n"
)


def python_home(platform: str, cache: Path) -> Path:
    """The pinned CPython for ``platform``, downloaded once into ``cache`` and checked against its digest."""
    spec = PLATFORMS[platform]
    home = cache / spec["pbs"].removesuffix(".tar.gz") / "python"
    # Reuse the cache only when it holds the interpreter: an empty or half-extracted
    # directory would build a package without Python.
    if (home / "python.exe").is_file() or (home / "bin" / "python3").is_file():
        return home
    archive = cache / spec["pbs"]
    if not archive.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PBS_URL + urllib.parse.quote(spec["pbs"]), archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        archive.unlink()
        raise RuntimeError(f"{spec['pbs']} has SHA-256 {digest}, expected {spec['sha256']}")
    with tarfile.open(archive) as bundle:
        bundle.extractall(home.parent, filter="data")
    return home


def build(core_wheel: Path, platform: str, output_dir: Path, cache: Path) -> Path:
    spec = PLATFORMS[platform]
    windows = platform.startswith("windows")
    if not core_wheel.name.endswith(f"-{spec['wheel_tag']}.whl"):
        raise RuntimeError(f"{core_wheel.name} is not a {spec['wheel_tag']} wheel; {platform} needs one")
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        module = stage / "module"
        (module / "plug-ins").mkdir(parents=True)
        (module / "scripts").mkdir()
        shutil.copy2(ROOT / "maya" / "plugin" / "meshy_dcc_maya_plugin.py", module / "plug-ins")
        shutil.copy2(ROOT / "maya" / "userSetup.py", module / "scripts")
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                sys.executable,
                "--python-platform",
                spec["uv_platform"],
                "--target",
                str(module / "python"),
                "--no-deps",
                str(core_wheel),
                str(ROOT),
                "packaging==24.2",
            ],
            check=True,
        )
        site = module / "python"
        shutil.rmtree(site / "bin", ignore_errors=True)
        shutil.rmtree(site / "Scripts", ignore_errors=True)
        (site / ".lock").unlink(missing_ok=True)
        strip_build_paths(site)

        shutil.copytree(python_home(platform, cache), stage / "python", ignore=_trimmed)
        for pycache in stage.rglob("__pycache__"):
            shutil.rmtree(pycache)

        (stage / "bin").mkdir()
        if windows:
            launcher = stage / "bin" / "meshy-dcc-maya.cmd"
            launcher.write_bytes(WINDOWS_LAUNCHER.encode("ascii"))
        else:
            launcher = stage / "bin" / "meshy-dcc-maya"
            launcher.write_text(POSIX_LAUNCHER, encoding="utf-8")
        launcher.chmod(0o755)

        missing = [p for p in ("module/python/meshy_dcc_core/__init__.py", INSTALLER) if not (stage / p).is_file()]
        if missing:
            raise RuntimeError(f"package is missing {missing}")
        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy-dcc-maya-{platform}.zip"
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
        kept = [
            line
            for line in lines
            if not line.startswith(tuple(dropped)) and not line.startswith(("bin/", "Scripts/", "../"))
        ]
        record.write_text("".join(kept), encoding="utf-8")


def write_zip(root: Path, archive: Path) -> None:
    """Zip ``root`` with sorted entries, fixed timestamps and Unix modes; no symlinks."""
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(p for p in root.rglob("*") if p.is_file() or p.is_symlink()):
            if path.is_symlink():
                raise RuntimeError(f"refusing to package a symlink: {path.relative_to(root)}")
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
    archive = build(args.core_wheel, args.platform, args.output_dir, args.python_cache)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
