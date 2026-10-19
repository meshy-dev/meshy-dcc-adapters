"""Install the Meshy DCC startup loader into Substance 3D Painter's user profile.

Painter loads every module in ``<profile>/python/startup`` when it starts; the
profile is ``<Documents>/Adobe/Adobe Substance 3D Painter``. ``install`` writes
one module there, a loader that puts the folder holding this package and
``meshy_dcc_core`` on ``sys.path`` and starts the adapter. ``uninstall``
removes that module. Nothing else in the profile or the Painter install is
touched, and a file of the same name that this installer did not write is
never overwritten or deleted.

    meshy-dcc-substance3d-painter install | uninstall | status [--yes] [--json]

Without ``--yes``, install and uninstall only report what they would do.
Exit codes: 0 done, 10 refused (a foreign file is in the way, or the payload
is incomplete), 30 the profile could not be written.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from meshy_dcc_substance3d_painter.__version__ import __version__

COMMAND = "meshy-dcc-substance3d-painter"
DCC_TYPE = "substance3d_painter"
PROFILE_ENV = "MESHY_DCC_SUBSTANCE3D_PAINTER_PROFILE"
LOADER_NAME = "meshy_dcc_substance3d_painter_plugin.py"
MARKER = '"""Meshy DCC startup loader for Substance 3D Painter.'
EXIT_OK, EXIT_REFUSED, EXIT_WRITE = 0, 10, 30

LOADER_TEMPLATE = (
    MARKER + "\n\n"
    "Written by `" + COMMAND + " install`; `" + COMMAND + " uninstall` removes it.\n"
    '"""\n\n'
    "import os\n"
    "import sys\n\n"
    "PAYLOAD = {payload!r}\n"
    "if not os.path.isdir(PAYLOAD):\n"
    "    raise ImportError(\n"
    '        "Meshy DCC is no longer installed at " + PAYLOAD + ". Run `meshy-dcc install --dcc-type "\n'
    '        "substance3d_painter`, or delete " + __file__\n'
    "    )\n"
    "if PAYLOAD not in sys.path:\n"
    "    sys.path.insert(0, PAYLOAD)\n\n"
    "from meshy_dcc_substance3d_painter.painter.startup.meshy_dcc_substance3d_painter_plugin import (  # noqa: E402\n"
    "    close_plugin,\n"
    "    start_plugin,\n"
    ")\n\n"
    '__all__ = ["close_plugin", "start_plugin"]\n'
)


def documents_dir() -> Path:
    """The user's Documents folder as Painter sees it (redirected folders included on Windows)."""
    if os.name == "nt":
        import ctypes  # noqa: PLC0415 - Windows only

        buffer = ctypes.create_unicode_buffer(32768)
        # CSIDL_PERSONAL: the shell's Documents folder, which follows OneDrive or policy redirection.
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0 and buffer.value:
            return Path(buffer.value)
    return Path.home() / "Documents"


def profile_dir(environ: Mapping[str, str] = os.environ) -> Path:
    override = environ.get(PROFILE_ENV, "").strip()
    if override:
        return Path(os.path.abspath(os.path.expanduser(override)))
    return documents_dir() / "Adobe" / "Adobe Substance 3D Painter"


def payload_dir() -> Path:
    """The folder that holds this package and ``meshy_dcc_core`` (links are not followed)."""
    return Path(os.path.abspath(__file__)).parents[1]


def loader_path(environ: Mapping[str, str] = os.environ) -> Path:
    return profile_dir(environ) / "python" / "startup" / LOADER_NAME


def bytecode_dir(profile: Path, source_dir: Path) -> Path:
    """Where Painter 12 caches bytecode for modules in ``source_dir``.

    Painter sets ``sys.pycache_prefix`` to ``<profile>/pycache``, so Python
    mirrors each source folder there, drive letter dropped.
    """
    return profile / "pycache" / os.path.splitdrive(str(source_dir))[1].lstrip("\\/")


def remove_bytecode(profile: Path, loader: Path, payload: Optional[str]) -> None:
    """Remove the bytecode Painter cached for the loader and for the payload it loaded.

    Older Painters write it to ``__pycache__`` next to the loader instead.
    Other plugins may share every folder here, so only folders left empty go.
    """
    prefix = profile / "pycache"
    beside = loader.parent / "__pycache__"
    mirrors = [bytecode_dir(profile, loader.parent)]
    for cache in (beside, mirrors[0]):
        for compiled in cache.glob(loader.stem + ".*.pyc"):
            compiled.unlink()
    if beside.is_dir() and not any(beside.iterdir()):
        beside.rmdir()
    if payload:
        mirrors.append(bytecode_dir(profile, Path(payload)))
        shutil.rmtree(mirrors[-1], ignore_errors=True)
    for cache in mirrors:
        while prefix in cache.parents and not (cache.is_dir() and any(cache.iterdir())):
            if cache.is_dir():
                cache.rmdir()
            cache = cache.parent


def loader_source(payload: Path) -> str:
    return LOADER_TEMPLATE.format(payload=str(payload))


def read_loader(path: Path) -> Tuple[str, Optional[str]]:
    """``(state, payload)``: state is ``missing``, ``ours`` or ``foreign``."""
    if not path.exists() and not path.is_symlink():
        return "missing", None
    if path.is_symlink() or not path.is_file():
        return "foreign", None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "foreign", None
    if not text.startswith(MARKER):
        return "foreign", None
    for line in text.splitlines():
        if line.startswith("PAYLOAD = "):
            try:
                return "ours", str(ast.literal_eval(line[len("PAYLOAD = ") :]))
            except (ValueError, SyntaxError):
                break
    return "ours", None


def run(verb: str, yes: bool, environ: Mapping[str, str] = os.environ) -> Tuple[int, Dict[str, Any]]:
    target = loader_path(environ)
    payload = payload_dir()
    state, recorded = read_loader(target)
    result: Dict[str, Any] = {
        "schema_version": 1,
        "verb": verb,
        "dcc_type": DCC_TYPE,
        "adapter_version": __version__,
        "profile": str(profile_dir(environ)),
        "loader_path": str(target),
        "payload": str(payload),
        "applied": False,
    }

    def done(code: int, status: str, message: str) -> Tuple[int, Dict[str, Any]]:
        result.update(status=status, message=message)
        return code, result

    if verb == "status":
        result.update(installed_payload=recorded, payload_exists=bool(recorded) and os.path.isdir(recorded or ""))
        if state == "missing":
            return done(EXIT_OK, "not_installed", "No Meshy DCC loader in the Painter profile.")
        if state == "foreign":
            return done(EXIT_OK, "foreign", f"{target} exists but was not written by this installer.")
        current = recorded == str(payload)
        return done(
            EXIT_OK,
            "installed" if current else "installed_other",
            "Painter loads Meshy DCC from " + str(recorded) + ("" if current else " (another package)."),
        )

    if state == "foreign":
        return done(
            EXIT_REFUSED,
            "refused",
            f"{target} was not written by this installer; move it out of Painter's startup folder, then retry.",
        )

    if verb == "uninstall":
        if state == "missing":
            return done(EXIT_OK, "not_installed", "Nothing to remove.")
        if not yes:
            return done(EXIT_OK, "planned", f"Would remove {target}.")
        try:
            target.unlink()
            remove_bytecode(profile_dir(environ), target, recorded)
        except OSError as exc:
            return done(EXIT_WRITE, "failed", f"Could not remove {target}: {exc}")
        result["applied"] = True
        return done(EXIT_OK, "uninstalled", f"Removed {target}. Painter stops loading Meshy DCC at its next start.")

    # install
    if not (payload / "meshy_dcc_core").is_dir() or not (payload / "meshy_dcc_substance3d_painter").is_dir():
        return done(EXIT_REFUSED, "refused", f"{payload} does not hold meshy_dcc_core and this adapter.")
    source = loader_source(payload)
    if state == "ours" and target.read_text(encoding="utf-8") == source:
        return done(EXIT_OK, "current", "The Painter profile already loads this package.")
    if not yes:
        return done(EXIT_OK, "planned", f"Would write {target}, loading Meshy DCC from {payload}.")
    temporary = target.with_name(f".{LOADER_NAME}.{os.getpid()}.tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(source, encoding="utf-8")
        os.replace(temporary, target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        return done(EXIT_WRITE, "failed", f"Could not write {target}: {exc}")
    result["applied"] = True
    return done(
        EXIT_OK,
        "installed",
        f"Wrote {target}. Painter loads Meshy DCC the next time it starts; restart it if it is running.",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog=COMMAND, description=__doc__.splitlines()[0])
    parser.add_argument("verb", choices=("install", "uninstall", "status"))
    parser.add_argument("--yes", action="store_true", help="apply the change (default: report the plan)")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    code, result = run(args.verb, args.yes)
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(result["message"], file=sys.stdout if code == EXIT_OK else sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
