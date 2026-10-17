"""``meshy-dcc-roblox`` command line: install verbs, ``launch`` and ``serve``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import install

STUDIO_ENV = "MESHY_DCC_ROBLOX_STUDIO"


def find_studio() -> Path:
    """Roblox Studio's executable (``MESHY_DCC_ROBLOX_STUDIO`` overrides)."""
    override = os.environ.get(STUDIO_ENV)
    if override:
        candidates = [Path(override)]
    elif sys.platform == "darwin":
        app = Path("RobloxStudio.app/Contents/MacOS/RobloxStudio")
        candidates = [Path("/Applications") / app, Path.home() / "Applications" / app]
    elif os.name == "nt":
        # Every Studio update installs into a new Versions/version-<hash> folder.
        roots = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "Versions",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Roblox" / "Versions",
        ]
        found = [path for root in roots for path in root.glob("*/RobloxStudioBeta.exe")]
        candidates = sorted(found, key=lambda path: path.stat().st_mtime, reverse=True)
    else:
        candidates = []
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise install.InstallError(f"Roblox Studio was not found; set {STUDIO_ENV} to its executable")


def studio_command(project: Path) -> tuple:
    """Studio's argv for the project's place, and the place the plugin must report."""
    config = install.read_config(project)
    studio = str(find_studio())
    if "place_id" in config:
        argv = [studio, "--task", "EditPlace", "--placeId", str(config["place_id"]),
                "--universeId", str(config["universe_id"])]
        return argv, {"place_id": config["place_id"]}
    place = project.absolute() / config["place_file"]
    return [studio, "--task", "EditFile", "--localPlaceFile", str(place)], {"place_file": place.name}


def _print(report: dict) -> None:
    print(json.dumps(report, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-roblox")
    verbs = parser.add_subparsers(dest="verb", required=True)
    add = verbs.add_parser("install", help="Install the Studio plugin and bind a project to a place")
    add.add_argument("--project", type=Path, required=True)
    add.add_argument("--place", help="Place file inside the project (default: its only .rbxl/.rbxlx)")
    add.add_argument("--place-id", type=int, help="A published place to open instead of a file")
    add.add_argument("--universe-id", type=int)
    remove = verbs.add_parser("uninstall", help="Remove a project's binding and/or the plugin")
    remove.add_argument("--project", type=Path)
    remove.add_argument("--plugin", action="store_true", help="Also remove the Studio plugin")
    show = verbs.add_parser("status")
    show.add_argument("--project", type=Path)
    launch = verbs.add_parser("launch", help="Open the project's place in Studio and serve it")
    launch.add_argument("--project", type=Path, required=True)
    verbs.add_parser("serve", help="Serve whichever Studio place connects first (diagnostics)")
    args = parser.parse_args(argv)

    try:
        if args.verb == "install":
            _print(install.install(args.project, args.place, args.place_id, args.universe_id))
        elif args.verb == "uninstall":
            _print(install.uninstall(args.project, args.plugin))
        elif args.verb == "status":
            _print(install.status(args.project))
        elif args.verb == "launch":
            studio_argv, expect = studio_command(args.project)
            from . import server

            server.main(expect=expect, studio_argv=studio_argv)
        else:
            from . import server

            server.main()
    except install.InstallError as exc:
        _print({"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
