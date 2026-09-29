"""Canonical Godot adapter command line."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from . import install, server

LIFECYCLE_VERBS = {"install", "status", "verify", "uninstall", "upgrade"}


def main(argv: Sequence[str] | None = None) -> int:
    """Route lifecycle verbs; otherwise serve (``serve`` is optional)."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in LIFECYCLE_VERBS:
        return install.main(arguments)
    if arguments[:1] == ["serve"]:
        arguments = arguments[1:]
    parser = argparse.ArgumentParser(prog="meshy-dcc-godot serve")
    parser.add_argument("--watch-pid", type=int, help="Exit when this process (the editor) exits.")
    parser.add_argument("--bridge-port", type=int, help="Loopback port the EditorPlugin dials.")
    options = parser.parse_args(arguments)
    if options.bridge_port:
        os.environ["MESHY_DCC_GODOT_BRIDGE_PORT"] = str(options.bridge_port)
    server.main(watch_pid=options.watch_pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
