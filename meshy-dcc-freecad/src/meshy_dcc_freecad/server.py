from __future__ import annotations

import os
import signal
import threading
import time
from pathlib import Path
from typing import Any, Optional

from meshy_dcc_core import DccServerOptions
from meshy_dcc_core.server_base import DccServerBase

from .__version__ import __version__

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"
HOST_VERSION_ENV = "MESHY_DCC_FREECAD_HOST_VERSION"

_server: Optional["FreecadMcpServer"] = None
_stopped = threading.Event()


class FreecadMcpServer(DccServerBase):
    def __init__(
        self,
        port: Optional[int] = None,
        *,
        gateway_port: Optional[int] = None,
        enable_gateway_failover: bool = True,
    ):
        options = DccServerOptions.from_env(
            "freecad",
            Path(__file__).parent / "skills",
            port=port,
            gateway_port=gateway_port,
            enable_gateway_failover=enable_gateway_failover,
            server_name="meshy-dcc-freecad",
            server_version=__version__,
            adapter_version=__version__,
            instance_type="standalone",
        )
        super().__init__(options=options)

    def _version_string(self):
        # The FreeCAD release the installer verified, so `list` shows the host's version.
        return os.environ.get(HOST_VERSION_ENV) or __version__


def handle_stop_request(body: dict, instance_id: Any) -> tuple[int, dict]:
    """Decide one safe-stop request from ``meshy-dcc stop-instance``.

    Every call saves before it returns, so nothing is ever unsaved; the only
    work a stop can lose is a FreeCAD call still running. That refuses unless
    the caller passes ``discard_unsaved``, which cancels the call: a mutation
    only replaces its document after FreeCAD saved and read it back, so the
    document stays as it was. The service exits once no call is running.
    """
    from .bridge import running_calls

    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    running = running_calls()
    if running and body.get("discard_unsaved") is not True:
        return 409, {
            "stopping": False,
            "reason": "call_in_progress",
            "detail": "A FreeCAD call is still running. Wait for it, or stop with "
            "--discard-unsaved to cancel it; its document stays as it was before the call.",
        }
    _mark_stopping()
    threading.Thread(target=_stop_when_idle, name="meshy-dcc-freecad-stop", daemon=True).start()
    return 202, {"stopping": True, "cancelled_calls": len(running)}


def _mark_stopping() -> None:
    """Refuse new FreeCAD calls and cancel running ones (see bridge._check_stopping)."""
    from .bridge import RUN_DIR_ENV, STOPPING_MARKER

    run_dir = os.environ.get(RUN_DIR_ENV)
    if run_dir:
        Path(run_dir, STOPPING_MARKER).touch()


def _stop_when_idle(limit_secs: float = 30.0) -> None:
    from .bridge import running_calls

    deadline = time.monotonic() + limit_secs
    while running_calls() and time.monotonic() < deadline:
        time.sleep(0.1)
    time.sleep(0.5)  # let the stop reply reach the caller
    _stopped.set()


def attach_safe_stop(server: FreecadMcpServer) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    handle = getattr(server, "_handle", None)
    if not os.environ.get(START_OPERATION_ENV) or handle is None:
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})


def start_server(port: Optional[int] = None):
    global _server
    if _server is None or not _server.is_running:
        _server = FreecadMcpServer(port)
        _server.register_builtin_actions()
        _server.start()
        attach_safe_stop(_server)
    return _server


def stop_server():
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def main():
    signal.signal(signal.SIGINT, lambda *_: _stopped.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: _stopped.set())
    start_server()
    try:
        _stopped.wait()
    finally:
        stop_server()


if __name__ == "__main__":
    main()
