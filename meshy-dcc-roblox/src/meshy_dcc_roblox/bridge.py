"""Loopback WebSocket bridge between the sidecar and the Roblox Studio plugin.

Studio plugins cannot listen, and they cannot learn which port a sidecar was
given, so the plugin probes the fixed ``PORTS`` (an HTTP GET answered here),
opens a WebSocket to one that is accepting and says ``hello`` with its place.
The sidecar was started for one place and binds only the plugin session of
that place; every other session is refused, so a call never reaches a
different Studio window. Browser origins are refused outright.
"""

from __future__ import annotations

import asyncio
import http
import json
import logging
import os
import socket
import threading
from typing import Any, Callable, Optional

from meshy_dcc_core import json_dumps
from meshy_dcc_core.bridge import BridgeConnectionError, DccBridge

from .__version__ import __version__

logger = logging.getLogger(__name__)

# Keep in step with PORTS in plugin/MeshyDcc.lua.
PORTS = (13890, 13891, 13892, 13893)

_bridge: Optional[RobloxBridge] = None
_lock = threading.Lock()


def place_matches(expect: dict, place: dict) -> bool:
    """Whether a plugin's place is the one this sidecar was started for."""
    if not expect:
        return True
    if "place_id" in expect:
        return place.get("place_id") == expect["place_id"]
    # A local place file opens unpublished (PlaceId 0); Studio names the
    # DataModel after the file, with or without its extension.
    wanted = str(expect.get("place_file", "")).lower()
    name = str(place.get("name", "")).lower()
    return place.get("place_id") in (0, None) and name in {wanted, wanted.rsplit(".", 1)[0]}


class RobloxBridge(DccBridge):
    """Core's WebSocket JSON-RPC bridge, bound to one Studio place."""

    def __init__(
        self,
        port: int,
        expect: Optional[dict] = None,
        on_change: Optional[Callable[[], None]] = None,
        timeout: float = 120.0,
    ) -> None:
        super().__init__(
            host="127.0.0.1",
            port=port,
            timeout=timeout,
            server_name="meshy-dcc-roblox",
            server_version=__version__,
        )
        self.expect = dict(expect or {})
        self.place: Optional[dict] = None
        self.studio_version: Optional[str] = None
        self._on_change = on_change or (lambda: None)

    async def _handle_hello(self, msg: dict, ws: Any) -> None:
        place = msg.get("place") if isinstance(msg.get("place"), dict) else {}
        reason = None
        if self._connected and self._ws is not ws:
            reason = "busy"
        elif not place_matches(self.expect, place):
            reason = "place_mismatch"
        if reason:
            logger.info("Refused Studio session for place %r: %s", place, reason)
            reject = {"type": "hello_reject", "reason": reason, "expect": self.expect}
            await self._send(json_dumps(reject), ws)
            await ws.close()
            return
        self.place = place
        self.studio_version = msg.get("version") if isinstance(msg.get("version"), str) else None
        await super()._handle_hello(msg, ws)
        self._on_change()

    async def _handle_dcc(self, ws: Any) -> None:
        try:
            await super()._handle_dcc(ws)
        finally:
            if not self._connected and self.place is not None:
                self.place = None
                self._on_change()

    async def _serve(self) -> None:
        import websockets

        def process_request(connection: Any, request: Any) -> Any:
            origin = request.headers.get("Origin", "")
            if origin.startswith(("http://", "https://")):
                return connection.respond(http.HTTPStatus.FORBIDDEN, "Browser origins are refused.\n")
            if request.headers.get("Upgrade", "").lower() != "websocket":
                probe = {
                    "server": "meshy-dcc-roblox",
                    "version": __version__,
                    "accepting": not self._connected,
                }
                return connection.respond(http.HTTPStatus.OK, json.dumps(probe) + "\n")
            return None

        shutdown_event = asyncio.Event()
        self._shutdown_event = shutdown_event
        try:
            async with websockets.serve(
                self._handle_dcc,
                self._host,
                self._port,
                process_request=process_request,
                max_size=8 * 2**20,
            ) as server:
                self._ws_server = server
                self._server_ready.set()
                await shutdown_event.wait()
        finally:
            self._shutdown_event = None
            self._ws_server = None


def pick_port() -> int:
    """The first free port of ``PORTS`` (``MESHY_DCC_ROBLOX_BRIDGE_PORT`` overrides)."""
    forced = os.environ.get("MESHY_DCC_ROBLOX_BRIDGE_PORT")
    if forced:
        return int(forced)
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise BridgeConnectionError(
        f"Every Roblox bridge port ({PORTS[0]}-{PORTS[-1]}) is taken: "
        f"at most {len(PORTS)} Studio places can be served at once."
    )


def get_bridge() -> Optional[RobloxBridge]:
    """The running bridge, or None before ``start_bridge``."""
    return _bridge


def start_bridge(
    expect: Optional[dict] = None, on_change: Optional[Callable[[], None]] = None
) -> RobloxBridge:
    global _bridge
    with _lock:
        if _bridge is not None:
            raise BridgeConnectionError("The Roblox bridge is already running.")
        _bridge = RobloxBridge(
            port=pick_port(),
            expect=expect,
            on_change=on_change,
            timeout=float(os.environ.get("MESHY_DCC_ROBLOX_BRIDGE_TIMEOUT", "120")),
        )
        bridge = _bridge
    bridge.connect(wait_for_dcc=False)
    logger.info("Roblox bridge listening on %s for %r", bridge.endpoint, bridge.expect)
    return bridge


def stop_bridge() -> None:
    global _bridge
    with _lock:
        bridge, _bridge = _bridge, None
    if bridge is not None:
        bridge.disconnect()


def call_host(method: str, params: Optional[dict] = None) -> dict:
    """Run one plugin method in the bound Studio place and return its result."""
    bridge = _bridge
    if bridge is None:
        raise BridgeConnectionError("The Roblox bridge is not running.")
    result = bridge.call(method, **(params or {}))
    return result if isinstance(result, dict) else {"value": result}
