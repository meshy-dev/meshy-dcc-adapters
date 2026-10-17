"""Command-line entry point for meshy-dcc-zbrush sidecar mode."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

from meshy_dcc_zbrush import start_server, stop_server
from meshy_dcc_zbrush.__version__ import __version__

LIFECYCLE_OPERATIONS = {"install", "status", "verify", "uninstall", "upgrade"}


def _asset_dir_from_environment() -> Optional[Path]:
    explicit = os.environ.get("ZBRUSH_USER_ASSETS_DIR")
    if explicit:
        return Path(explicit)
    plugin_path = os.environ.get("ZBRUSH_PLUGIN_PATH", "")
    if plugin_path:
        first = plugin_path.split(os.pathsep, 1)[0]
        if first:
            return Path(first)
    return None


def _lifecycle_main(argv: list[str]) -> int:
    from meshy_dcc_zbrush.install_lifecycle import LifecycleRequest, run_lifecycle

    parser = argparse.ArgumentParser(description="Install and verify the ZBrush MCP adapter")
    parser.add_argument("operation", choices=sorted(LIFECYCLE_OPERATIONS))
    parser.add_argument("--mode", choices=("embedded", "sidecar"), default="sidecar")
    parser.add_argument("--version", default=__version__, help="Fixed adapter release version (never 'latest')")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit the stable lifecycle JSON schema")
    parser.add_argument("--yes", action="store_true", help="Confirm a mutating install, upgrade, or uninstall")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run preflight and print the plan without changing files"
    )
    parser.add_argument("--dcc-path", type=Path, default=os.environ.get("ZBRUSH_EXECUTABLE"))
    parser.add_argument("--python", type=Path, default=Path(sys.executable), dest="python_path")
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=_asset_dir_from_environment(),
        help="ZBrush Asset Directory (or set ZBRUSH_USER_ASSETS_DIR)",
    )
    parser.add_argument("--socket-host", default="127.0.0.1")
    parser.add_argument("--socket-port", type=int, default=19876)
    parser.add_argument(
        "--plugin-archive",
        type=Path,
        help="Offline/local plugin ZIP; requires --sha256 and never bypasses verification",
    )
    parser.add_argument("--sha256", help="Expected SHA-256 for --plugin-archive")
    args = parser.parse_args(argv)
    request = LifecycleRequest(
        operation=args.operation,
        mode=args.mode,
        version=args.version,
        dcc_path=Path(args.dcc_path) if args.dcc_path else None,
        python_path=args.python_path,
        asset_dir=args.asset_dir,
        yes=args.yes,
        dry_run=args.dry_run,
        socket_host=args.socket_host,
        socket_port=args.socket_port,
    )
    result = run_lifecycle(
        request,
        plugin_archive=args.plugin_archive,
        expected_sha256=args.sha256,
    )
    if args.json_output:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"{result['status']}: {result['reason']}")
        for step in result["next_steps"]:
            action = step.get("command") or step.get("file_edit")
            print(f"- {step['description']} ({action})")
    return int(result["exit_code"])


def _watch_host(pid: int, stopped: threading.Event) -> None:
    from meshy_dcc_core._install_lifecycle_process import is_pid_alive  # noqa: PLC0415

    while not stopped.wait(1.0):
        if not is_pid_alive(pid):
            stopped.set()


def main(argv: Optional[list[str]] = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] in LIFECYCLE_OPERATIONS:
        return _lifecycle_main(arguments)
    if arguments[:1] == ["setup-project"]:
        from meshy_dcc_zbrush.project_setup import main as setup_main  # noqa: PLC0415

        return setup_main(arguments[1:])
    if arguments[:1] == ["serve"]:
        arguments = arguments[1:]
    parser = argparse.ArgumentParser(prog="meshy-dcc-zbrush serve", description="ZBrush MCP Server")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Optional fixed MCP instance port (default: core/env, then OS-assigned)",
    )
    parser.add_argument(
        "--gateway-port", type=int, default=None, help="Gateway port (None = core default 19765, 0 = disabled)"
    )
    parser.add_argument(
        "--mode",
        choices=("embedded", "sidecar"),
        default=None,
        help="embedded when running inside ZBrush; sidecar when using socket plugin",
    )
    parser.add_argument("--socket-host", default="127.0.0.1", help="ZBrush socket plugin host")
    parser.add_argument("--socket-port", type=int, default=19876, help="ZBrush socket plugin port")
    parser.add_argument("--watch-pid", type=int, help="ZBrush process to bind to; exit when it exits")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(arguments)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    server = start_server(
        port=args.port,
        gateway_port=args.gateway_port,
        mode=args.mode or "sidecar",
        socket_host=args.socket_host,
        socket_port=args.socket_port,
        dcc_pid=args.watch_pid,
    )

    print(f"ZBrush MCP server started ({server.mode}): {server.mcp_url}")
    if args.watch_pid:
        threading.Thread(target=_watch_host, args=(args.watch_pid, stopped), daemon=True).start()
    try:
        stopped.wait()
    finally:
        stop_server()
    return 0


if __name__ == "__main__":
    sys.exit(main())
