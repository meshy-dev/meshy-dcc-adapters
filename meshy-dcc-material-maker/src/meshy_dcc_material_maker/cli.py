"""``meshy-dcc-material-maker``: the sidecar, its project installer, or a diagnostic verb."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

# The managed-root Install SOP kept from the original adapter (diagnostics).
LIFECYCLE_COMMANDS = {"install", "status", "verify", "uninstall", "upgrade", "doctor", "configure"}
LIFECYCLE_FLAGS = {"--json", "--yes", "--dry-run", "--execute", "--dcc-path", "--python"}
PROJECT_COMMANDS = {"install-project", "uninstall-project"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] and args[0] in PROJECT_COMMANDS:
        from .project_install import main as project_main

        return project_main(args)
    if args[:1] == ["serve"]:
        parser = argparse.ArgumentParser(prog="meshy-dcc-material-maker serve")
        parser.add_argument("--project", help="Material project folder the tools work in")
        options = parser.parse_args(args[1:])
        from .server import serve

        serve(options.project)
        return 0
    if args and (args[0] in LIFECYCLE_COMMANDS or any(item in LIFECYCLE_FLAGS for item in args)):
        from .install import main as diagnostic_main

        diagnostic_main(args, program="meshy-dcc-material-maker")
        return 0
    if args:
        print("usage: meshy-dcc-material-maker [serve --project DIR | install-project DIR ...]", file=sys.stderr)
        return 2
    from .server import serve

    serve(None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
