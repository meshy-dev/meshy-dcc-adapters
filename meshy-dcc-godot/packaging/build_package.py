"""Build the Meshy DCC Godot package: the sidecar with its own Python.

Godot has no Python of its own, so the package carries a relocatable CPython
(python-build-standalone, the kind uv installs) with ``meshy_dcc_core``, this
adapter and ``websockets`` installed into it::

    python/                          CPython and its site-packages
    bin/meshy-dcc-godot-sidecar      runs ``python -m meshy_dcc_godot``

The EditorPlugin ships inside ``meshy_dcc_godot/godot_addon``.
``meshy-dcc install --dcc-type godot --project <root>`` extracts the zip and
runs the bundled installer against the project.

Usage::

    python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> --output-dir dist
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.11"
# Trimmed from the runtime: tests, GUI toolkits and build headers the sidecar never loads.
EXCLUDED = shutil.ignore_patterns(
    "__pycache__",
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
)
SIDECAR_SCRIPT = """#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/../python/bin/python{version}" -m meshy_dcc_godot "$@"
"""


def adapter_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("version is missing from pyproject.toml")
    return match.group(1)


def default_python_home() -> Path:
    """The uv-managed CPython install for PYTHON_VERSION."""
    executable = subprocess.run(
        ["uv", "python", "find", "--managed-python", PYTHON_VERSION],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(executable).resolve().parents[1]


def platform_tag() -> str:
    machine = os.uname().machine if hasattr(os, "uname") else "x86_64"
    system = {"darwin": "macos", "linux": "linux"}.get(sys.platform, sys.platform)
    return f"{system}_{'arm64' if machine in {'arm64', 'aarch64'} else 'x86_64'}"


def build(core_wheel: Path, python_home: Path, output_dir: Path) -> Path:
    version = adapter_version()
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "package"
        shutil.copytree(python_home, stage / "python", symlinks=False, ignore=EXCLUDED)
        python = stage / "python" / "bin" / f"python{PYTHON_VERSION}"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                str(core_wheel),
                str(ROOT),
                "websockets>=12,<18",
            ],
            check=True,
        )
        for cache in stage.rglob("__pycache__"):
            shutil.rmtree(cache)
        sidecar = stage / "bin" / "meshy-dcc-godot-sidecar"
        sidecar.parent.mkdir()
        sidecar.write_text(SIDECAR_SCRIPT.format(version=PYTHON_VERSION), encoding="utf-8")
        sidecar.chmod(0o755)

        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"meshy_dcc_godot_{platform_tag()}_v{version}.zip"
        write_zip(stage, archive)
    return archive


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
    parser.add_argument("--python-home", type=Path, help="Relocatable CPython root (default: uv's)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build(args.core_wheel, args.python_home or default_python_home(), args.output_dir)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"{archive}\nsha256 {digest}")


if __name__ == "__main__":
    main()
