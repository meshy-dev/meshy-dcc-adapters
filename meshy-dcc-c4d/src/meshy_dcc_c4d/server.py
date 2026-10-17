from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from meshy_dcc_core import DccServerOptions
from meshy_dcc_core.server_base import DccServerBase

from .__version__ import __version__

_server: Optional["Cinema4dMcpServer"] = None
C4DPY_ENV = "MESHY_DCC_C4D_C4DPY"
ALLOWED_ROOTS_ENV = "MESHY_DCC_C4D_ALLOWED_ROOTS"
START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


class _ArgumentFailure(Exception):
    pass


class _LifecycleParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentFailure(message)


class Cinema4dMcpServer(DccServerBase):
    def __init__(self, port: Optional[int] = None):
        options = DccServerOptions.from_env(
            "c4d",
            Path(__file__).parent / "skills",
            port=port,
            server_name="meshy-dcc-c4d",
            server_version=__version__,
            adapter_version=__version__,
        )
        super().__init__(options=options)

    def _version_string(self):
        """The Cinema 4D release of the configured c4dpy, read from its file metadata."""
        c4dpy = os.environ.get(C4DPY_ENV)
        if c4dpy:
            from .install import _platform_file_metadata

            try:
                version = _platform_file_metadata(Path(c4dpy)).get("product_version")
            except Exception:  # noqa: BLE001 - a version label must never stop the server
                version = None
            if version:
                return version
        return "unknown"


def start_server(port: Optional[int] = None):
    global _server
    if _server is None or not _server.is_running:
        _server = Cinema4dMcpServer(port)
        _server.register_builtin_actions()
        _server.start()
    return _server


def stop_server():
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def _build_parser() -> argparse.ArgumentParser:
    parser = _LifecycleParser(
        prog="meshy-dcc-c4d", description="Run or manage the Cinema 4D adapter lifecycle."
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for operation in ("doctor", "install", "status", "verify", "uninstall", "upgrade"):
        command = subparsers.add_parser(
            operation, help="Plan, inspect, or execute the standalone c4dpy lifecycle."
        )
        command.add_argument("--json", action="store_true", dest="json_output")
        command.add_argument("--c4dpy", type=Path)
        command.add_argument("--python", type=Path, dest="python_executable")
        command.add_argument("--state-root", type=Path)
        command.add_argument("--timeout-secs", type=float, default=60.0)
        command.add_argument("--yes", action="store_true", dest="execute")
        if operation in ("install", "uninstall"):
            command.add_argument(
                "--project",
                type=Path,
                help="Set up (or remove) a folder for meshy-dcc start-instance instead.",
            )
    serve = subparsers.add_parser("serve", help="Run the adapter service.")
    serve.add_argument("--project", type=Path, help="Folder the service may read and write.")
    plan = subparsers.add_parser("plan", help="Plan an install, upgrade, or uninstall.")
    plan.add_argument("--target", choices=("install", "upgrade", "uninstall"), required=True)
    plan.add_argument("--json", action="store_true", dest="json_output")
    plan.add_argument("--c4dpy", type=Path)
    plan.add_argument("--python", type=Path, dest="python_executable")
    plan.add_argument("--state-root", type=Path)
    plan.add_argument("--timeout-secs", type=float, default=60.0)
    plan.set_defaults(execute=False)
    return parser


def _print_doctor_result(result: Mapping[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(result, sort_keys=True))
        return
    print("%s: %s" % (result.get("status", "unknown"), result.get("reason", "")))
    for step in result.get("next_steps", []):
        command = step.get("command") if isinstance(step, Mapping) else None
        if isinstance(command, list):
            print("next: %s" % " ".join(str(part) for part in command))


def handle_stop_request(body: Mapping[str, Any], instance_id: Any, stop: Any) -> tuple:
    """Stop this service for ``meshy-dcc stop-instance``.

    The service keeps no document in memory: every tool writes its result to
    disk before it returns, so there is never unsaved work to refuse over.
    """
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    stop()
    return 202, {"stopping": True}


def _attach_safe_stop(server: "Cinema4dMcpServer", event: threading.Event) -> None:
    """Advertise ``safe_stop_url`` only for a start-instance launch."""
    handle = getattr(server, "_handle", None)
    if not os.environ.get(START_OPERATION_ENV) or handle is None:
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, event.set))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})


def _run_server(project: Optional[Path] = None) -> None:
    if project is not None:
        from .project import configured_c4dpy

        project = project.expanduser().absolute()
        c4dpy = configured_c4dpy(project)
        if c4dpy:
            os.environ.setdefault(C4DPY_ENV, c4dpy)
        os.environ.setdefault(ALLOWED_ROOTS_ENV, str(project))
    event = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: event.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: event.set())
    server = start_server()
    try:
        _attach_safe_stop(server, event)
        event.wait()
    finally:
        stop_server()


def _run_project(args: argparse.Namespace) -> int:
    from .project import ProjectError, install_project, uninstall_project

    try:
        if args.command == "install":
            if args.c4dpy is None:
                raise ProjectError("c4dpy_missing", "Pass --c4dpy with Cinema 4D's c4dpy.")
            result = install_project(args.project, args.c4dpy, execute=args.execute)
        else:
            result = uninstall_project(args.project, execute=args.execute)
    except (OSError, ProjectError) as exc:
        result = {
            "status": "failed",
            "operation": args.command,
            "reason": getattr(exc, "code", "io_error"),
            "detail": str(exc),
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "failed" else 10


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the no-argument service or the official Install SOP lifecycle."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        _run_server()
        return 0
    from meshy_dcc_core.deployment import INSTALL_EXIT_PREFLIGHT

    from .install import LifecycleRequest, failure_outcome, run_lifecycle

    try:
        args = _build_parser().parse_args(arguments)
    except _ArgumentFailure:
        outcome = failure_outcome("arguments", "arguments", INSTALL_EXIT_PREFLIGHT)
        _print_doctor_result(outcome.result, json_output=True)
        return outcome.exit_code
    if args.command == "serve":
        _run_server(args.project)
        return 0
    if getattr(args, "project", None) is not None:
        return _run_project(args)
    operation = "verify" if args.command == "doctor" else args.command
    outcome = run_lifecycle(
        LifecycleRequest(
            operation=operation,
            executable=args.c4dpy,
            python_executable=args.python_executable,
            state_root=args.state_root,
            timeout_secs=args.timeout_secs,
            execute=args.execute,
            target=getattr(args, "target", None),
        )
    )
    outcome.result["requested_operation"] = args.command
    _print_doctor_result(outcome.result, json_output=args.json_output)
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
