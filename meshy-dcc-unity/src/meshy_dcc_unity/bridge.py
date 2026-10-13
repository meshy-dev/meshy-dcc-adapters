"""Loopback WebSocket bridge shared by the MCP server and Unity package."""

from __future__ import annotations

import math
import os
import threading
import time
from typing import Any

from meshy_dcc_core.bridge import BridgeConnectionError, DccBridge

_bridge: DccBridge | None = None
_lock = threading.Lock()
_HOST_REQUEST_LIFETIME_SECONDS = 55
_host_dispatch_ready = threading.Event()
# Wall-clock time Unity's main thread stopped answering; None while it answers.
_host_unresponsive_since: float | None = None

_HOST_BLOCKED_MESSAGE = (
    "Unity transport is connected, but the Editor main thread is not dispatching. "
    "A native modal dialog may be blocking Unity. Use Core UI Control with the same "
    "instance ID (`meshy-dcc ui-control`); MCP agents can search for ui-control "
    "and load the `app-ui` compatibility Skill. Bind the exact Unity PID/HWND "
    "through dcc-cua, dismiss the modal (for example Reload or Ignore), and retry."
)


def _bridge_timeout() -> float:
    value = float(os.environ.get("MESHY_DCC_UNITY_BRIDGE_TIMEOUT", "60"))
    if not math.isfinite(value) or value < 60:
        raise ValueError(
            "MESHY_DCC_UNITY_BRIDGE_TIMEOUT must be a finite value of at least 60 seconds"
        )
    return value


def get_bridge() -> DccBridge:
    """Return the process-wide bridge, creating it without starting it."""
    global _bridge
    with _lock:
        if _bridge is None:
            port = int(os.environ.get("MESHY_DCC_UNITY_BRIDGE_PORT", "13852"))
            _bridge = DccBridge(
                host="127.0.0.1",
                port=port,
                timeout=_bridge_timeout(),
                server_name="meshy-dcc-unity",
            )
            os.environ.setdefault("MESHY_DCC_UNITY_BRIDGE_URL", f"ws://127.0.0.1:{port}")
        return _bridge


def start_bridge() -> DccBridge:
    bridge = get_bridge()
    bridge.connect(wait_for_dcc=False)
    return bridge


def stop_bridge() -> None:
    global _bridge
    with _lock:
        bridge, _bridge = _bridge, None
    if bridge is not None:
        bridge.disconnect()
    set_host_dispatch_ready(False)


def set_host_dispatch_ready(ready: bool) -> None:
    """Publish whether Unity's main-thread update loop answered a live probe."""
    global _host_unresponsive_since
    if ready:
        _host_dispatch_ready.set()
        _host_unresponsive_since = None
    else:
        _host_dispatch_ready.clear()
        if _host_unresponsive_since is None:
            _host_unresponsive_since = time.time()


def host_unresponsive_since() -> float | None:
    """When Unity's main thread last stopped answering, or None while it answers."""
    return _host_unresponsive_since


def is_host_dispatch_ready() -> bool:
    return _host_dispatch_ready.is_set()


def probe_host_dispatch(deadline_seconds: float) -> None:
    """Send a raw main-thread probe without applying the public-call readiness guard."""
    get_bridge().call(
        "host.ping",
        _meshy_dcc_deadline_unix_ms=int((time.time() + deadline_seconds) * 1000),
    )


def call_host(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Invoke one typed command in the connected Unity Editor."""
    current_bridge = get_bridge()
    connected = getattr(current_bridge, "is_connected", None)
    if callable(connected) and connected() and not is_host_dispatch_ready():
        raise BridgeConnectionError(_HOST_BLOCKED_MESSAGE)
    request_params = dict(params or {})
    request_params["_meshy_dcc_deadline_unix_ms"] = int(
        (time.time() + _HOST_REQUEST_LIFETIME_SECONDS) * 1000
    )
    result = current_bridge.call(method, **request_params)
    return result if isinstance(result, dict) else {"value": result}
