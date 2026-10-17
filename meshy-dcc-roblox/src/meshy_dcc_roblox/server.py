"""Roblox Studio sidecar: the Meshy DCC server, the plugin bridge and Studio's lifetime."""

from __future__ import annotations

import logging
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

from meshy_dcc_core import AdapterReadinessBinder, DccServerOptions, HostExecutionBridge
from meshy_dcc_core.host import QueueDispatcher, StandaloneHost
from meshy_dcc_core.server_base import DccServerBase

from .__version__ import __version__
from .bridge import get_bridge, start_bridge, stop_bridge
from .dispatcher import RobloxBridgeDispatcher

logger = logging.getLogger(__name__)

# How long the sidecar outlives a Studio process that is gone while no plugin
# session is bound (Studio may hand a place to an already-running process).
STUDIO_GONE_GRACE_SECS = 30.0
_server: Optional["RobloxDccServer"] = None


class RobloxDccServer(DccServerBase):
    """Meshy DCC server whose tools run in Roblox Studio through the plugin."""

    def __init__(self, port: Optional[int] = None, expect: Optional[dict] = None) -> None:
        self.expect = dict(expect or {})
        self.studio: Optional[subprocess.Popen] = None
        self.stop_requested = threading.Event()
        self._host_dispatcher = QueueDispatcher()
        self._host_driver = StandaloneHost(self._host_dispatcher, thread_name="meshy-dcc-roblox-host")
        execution_bridge = HostExecutionBridge(
            dispatcher=RobloxBridgeDispatcher(),
            host_dispatcher=self._host_dispatcher,
            default_thread_affinity="main",
            default_execution="sync",
            default_timeout_hint_secs=120,
        )
        options = DccServerOptions.from_env(
            "roblox",
            Path(__file__).resolve().parent / "skills",
            port=port,
            server_name="meshy-dcc-roblox",
            server_version=__version__,
            execution_bridge=execution_bridge,
        )
        super().__init__(options=options)
        self._readiness_binder = AdapterReadinessBinder(self, dcc_ready_probe=self._bridge_connected)
        self._publish_state()

    def start(self, **kwargs: Any) -> Any:
        start_bridge(self.expect, on_change=self._publish_state)
        try:
            self._host_driver.start()
            handle = super().start(**kwargs)
            self._publish_state()
            from ._safe_stop import attach_safe_stop

            attach_safe_stop(self)
            return handle
        except Exception:
            self._host_driver.stop()
            stop_bridge()
            raise

    def stop(self) -> None:
        try:
            super().stop()
        finally:
            try:
                self._host_driver.stop()
            finally:
                stop_bridge()

    def _version_string(self) -> str:
        bridge = get_bridge()
        return (bridge.studio_version if bridge else None) or "unknown"

    @staticmethod
    def _bridge_connected() -> bool:
        bridge = get_bridge()
        return bridge is not None and bridge.is_connected()

    def _publish_state(self) -> None:
        """Mirror the plugin session into readiness bits and the instance context."""
        ready = self._bridge_connected()
        self._readiness_binder.mark_dispatcher_ready(
            True,
            dcc_ready=ready,
            host_execution_bridge_ready=ready,
            main_thread_executor_ready=ready,
        )
        bridge = get_bridge()
        if not ready or bridge is None or not bridge.place:
            return
        name = str(bridge.place.get("name") or "Roblox place")
        try:
            self.update_gateway_metadata(
                version=bridge.studio_version or "unknown",
                display_name=name,
                scene=name,
                documents=[],
            )
        except Exception as exc:  # noqa: BLE001 - the registry may not exist before start()
            logger.debug("Roblox context not published yet: %s", exc)


def start_server(expect: Optional[dict] = None) -> RobloxDccServer:
    global _server
    if _server is None or not _server.is_running:
        _server = RobloxDccServer(expect=expect)
        _server.register_builtin_actions()
        _server.start()
    return _server


def stop_server() -> None:
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def main(expect: Optional[dict] = None, studio_argv: Optional[list] = None) -> None:
    """Serve until interrupted, or until the launched Studio is gone.

    With ``studio_argv`` the sidecar starts Studio itself. It stays while the
    bound plugin session lives, since Studio may hand the place to a process
    that was already running, and exits once both the launched process and
    the session are gone.
    """
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    server = start_server(expect)
    try:
        if studio_argv:
            server.studio = subprocess.Popen(
                studio_argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Started Roblox Studio (pid %s): %s", server.studio.pid, studio_argv)
        gone_since: Optional[float] = None
        while not stopped.wait(1.0):
            studio = server.studio
            if studio is None or studio.poll() is None:
                gone_since = None
            elif server.stop_requested.is_set():
                break
            elif server._bridge_connected():
                gone_since = None  # the place lives on in another Studio process
            else:
                gone_since = gone_since or time.monotonic()
                if time.monotonic() - gone_since >= STUDIO_GONE_GRACE_SECS:
                    break
    finally:
        stop_server()

