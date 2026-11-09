"""SocketBridge — TCP JSON bridge to a ZBrush in-process plugin.

Use sidecar mode when the MCP server runs outside ZBrush and forwards tool
calls to ``bridge/plugin/mcp_socket_bridge.py`` running inside ZBrush.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 19876
# The bridge that starts the sidecar hands it this per-launch token.
TOKEN_ENV = "MESHY_DCC_ZBRUSH_BRIDGE_TOKEN"
DEFAULT_TIMEOUT_SEC = 610.0
PING_TIMEOUT_SEC = 3.0

# Busy retries. ZBrush services one SDK request at a time, so a concurrent call
# is refused rather than failed. Waiting it out is what makes the -32001
# "retryable" marker true; without this the marker is only a promise.
DEFAULT_BUSY_RETRIES = 3
DEFAULT_BUSY_BACKOFF_SEC = 0.25
DEFAULT_BUSY_BACKOFF_MAX_SEC = 2.0

STATUS_READY = "ready"
STATUS_BUSY = "busy"
STATUS_BLOCKED = "blocked"
STATUS_UNREACHABLE = "unreachable"

# Nothing listening on the port: a missing or dead plugin, not a blocked
# main thread. Distinguishing these keeps troubleshooting pointed the right way.
_UNREACHABLE_ERRORS = (ConnectionRefusedError, ConnectionResetError)

_BLOCKED_DETAIL = (
    "ZBrush is not executing Python: the main thread is inside a native call "
    "and no bridge request can be serviced. An open ZBrush Note has this "
    "signature, but so does any long native operation, so this is not proof "
    "of a dialog."
)


class ZBrushBridgeError(RuntimeError):
    """Raised when a bridge RPC call fails."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.data = dict(data or {})


class ZBrushBlockedError(RuntimeError):
    """Raised when ZBrush does not answer a ping within the probe timeout.

    Carries the ``probe()`` verdict in :attr:`detail` so callers can report the
    classification without re-parsing the message.
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.detail = dict(detail or {})


class ZBrushNotAvailableError(ConnectionError):
    """Raised when the ZBrush socket plugin is not reachable."""


# ``_send`` marks any exception raised after the TCP connection is up, i.e. once
# the request may be on the wire and the host may already be running it. A
# failure from ``create_connection`` proves nothing was sent and stays unmarked.
_POST_CONNECT_STAGE = "_zbrush_post_connect"


def _is_post_connect(exc: BaseException) -> bool:
    return bool(getattr(exc, _POST_CONNECT_STAGE, False))


class SocketBridge:
    """Minimal TCP JSON-RPC client for the ZBrush MCP socket plugin."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT_SEC,
        busy_retries: int = DEFAULT_BUSY_RETRIES,
        busy_backoff_sec: float = DEFAULT_BUSY_BACKOFF_SEC,
        busy_backoff_max_sec: float = DEFAULT_BUSY_BACKOFF_MAX_SEC,
        token: Optional[str] = None,
    ) -> None:
        self._host = host
        self._token = token if token is not None else (os.environ.get(TOKEN_ENV, "").strip() or None)
        self._port = port
        self._timeout = timeout
        self._busy_retries = max(0, int(busy_retries))
        self._busy_backoff_sec = max(0.0, float(busy_backoff_sec))
        self._busy_backoff_max_sec = max(self._busy_backoff_sec, float(busy_backoff_max_sec))
        self._connected = False

    @property
    def endpoint(self) -> str:
        return f"{self._host}:{self._port}"

    def connect(self) -> None:
        try:
            verdict = self.probe()
            if verdict["status"] == STATUS_BLOCKED:
                raise ZBrushBlockedError(verdict["message"], detail=verdict)
            if verdict["status"] == STATUS_UNREACHABLE:
                raise ZBrushNotAvailableError(
                    f"No ZBrush socket plugin listening at {self.endpoint}: {verdict.get('error')}"
                )
            self._connected = True
            logger.info("SocketBridge connected to %s", self.endpoint)
        except (ZBrushBlockedError, ZBrushNotAvailableError):
            raise
        except Exception as exc:
            raise ZBrushNotAvailableError(f"Cannot connect to ZBrush socket plugin at {self.endpoint}: {exc}") from exc

    def probe(self, timeout: float = PING_TIMEOUT_SEC) -> Dict[str, Any]:
        """Classify ZBrush's ability to service a request right now.

        Pings with a short timeout instead of waiting out the full request
        timeout, so a stalled host surfaces as an explicit verdict rather than a
        silent hang. Returns one of:

        * ``ready``       — answered, idle.
        * ``busy``        — answered, a request is in flight. Servable.
        * ``blocked``     — TCP reached a listening plugin but no answer arrived
          within ``timeout``; the main thread is inside a native call.
        * ``unreachable`` — nothing is listening. This is a plugin/installation
          problem, not a blocked main thread, and must not be reported as one.
        """
        payload = self._payload("ping", {})
        try:
            raw = self._send(json.dumps(payload).encode("utf-8"), timeout=timeout)
            message = json.loads(raw.decode("utf-8"))
        except _UNREACHABLE_ERRORS as exc:
            # A reset after the connection was accepted means the plugin is there
            # but its main thread did not answer: blocked, not "nothing listening".
            if _is_post_connect(exc):
                return {
                    "status": STATUS_BLOCKED,
                    "message": _BLOCKED_DETAIL,
                    "endpoint": self.endpoint,
                    "timeout_sec": timeout,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            return {
                "status": STATUS_UNREACHABLE,
                "message": (
                    f"No ZBrush socket plugin is listening at {self.endpoint}. "
                    "Start ZBrush with `meshy-dcc start-instance --dcc-type zbrush --project <folder>`."
                ),
                "endpoint": self.endpoint,
                "timeout_sec": timeout,
                "error": f"{type(exc).__name__}: {exc}",
            }
        except (TimeoutError, socket.timeout, json.JSONDecodeError, ZBrushBridgeError) as exc:
            return {
                "status": STATUS_BLOCKED,
                "message": _BLOCKED_DETAIL,
                "endpoint": self.endpoint,
                "timeout_sec": timeout,
                "error": f"{type(exc).__name__}: {exc}",
            }
        except OSError as exc:
            return {
                "status": STATUS_BLOCKED,
                "message": _BLOCKED_DETAIL,
                "endpoint": self.endpoint,
                "timeout_sec": timeout,
                "error": f"{type(exc).__name__}: {exc}",
            }

        error = message.get("error")
        if isinstance(error, dict) and error.get("code") == -32003:
            return {
                "status": STATUS_UNREACHABLE,
                "message": f"The ZBrush bridge at {self.endpoint} refused this sidecar's token.",
                "endpoint": self.endpoint,
                "timeout_sec": timeout,
                "error": str(error.get("message")),
            }
        result = message.get("result")
        if not isinstance(result, dict):
            return {
                "status": STATUS_BLOCKED,
                "message": _BLOCKED_DETAIL,
                "endpoint": self.endpoint,
                "timeout_sec": timeout,
                "error": f"Unexpected ping result: {result!r}",
            }

        busy = bool(result.get("busy"))
        active_method = result.get("active_method")
        if busy:
            return {
                "status": STATUS_BUSY,
                "message": f"ZBrush is servicing {active_method or 'a request'}",
                "endpoint": self.endpoint,
                "active_method": active_method,
                "timeout_sec": timeout,
            }
        return {
            "status": STATUS_READY,
            "message": "ZBrush is idle and can service requests",
            "endpoint": self.endpoint,
            "active_method": None,
            "timeout_sec": timeout,
        }

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def call(self, method: str, **params: Any) -> Any:
        """Send one RPC and return its result, waiting out a busy host.

        ZBrush services one SDK request at a time, so a concurrent call is
        refused with ``-32001`` and marked retryable. Retrying here is what
        makes that marker true: callers see a queued call instead of a failure.
        """
        attempts = self._busy_retries + 1
        for attempt in range(attempts):
            try:
                return self._call_once(method, **params)
            except ZBrushBridgeError as exc:
                if not self._is_retryable_busy(exc) or attempt == attempts - 1:
                    raise
                self._sleep_before_retry(attempt)
        raise AssertionError("unreachable")  # pragma: no cover

    def _call_once(self, method: str, **params: Any) -> Any:
        payload = self._payload(method, params)
        # Carry the wait budget across a delayed TCP accept: the plugin refuses a
        # queued request that expired before it started. The adapter is not handed
        # the caller's remaining budget, so the client timeout is the deadline.
        payload["deadline_unix_ms"] = (time.time() + self._timeout) * 1000

        def unknown_outcome(reason: str) -> ZBrushBridgeError:
            # Once a real method is on the wire the host may be running it, so a
            # lost or malformed reply leaves the outcome unknown. Replaying a
            # possibly side-effecting call is unsafe: never retryable.
            return ZBrushBridgeError(
                f"Lost or invalid ZBrush response after submitting {method}: {reason}. "
                "The outcome is unknown; inspect ZBrush before retrying.",
                code=-32002,
                data={"retryable": False, "execution_state": "unknown", "active_method": method},
            )

        try:
            raw = self._send(json.dumps(payload).encode("utf-8"))
        except OSError as exc:
            self._connected = False
            # Reset, abort, broken pipe, EOF or timeout after connect: unknown.
            # A failure before the connection was made is bare: nothing was sent.
            if _is_post_connect(exc):
                raise unknown_outcome(f"{type(exc).__name__}: {exc}") from exc
            raise
        try:
            message = json.loads(raw.decode("utf-8"))
            if not isinstance(message, dict) or not ({"result", "error"} & message.keys()):
                raise ValueError(f"not a JSON-RPC object: {raw!r}")
        except ValueError as exc:  # JSONDecodeError, UnicodeDecodeError, shape guard
            raise unknown_outcome(str(exc)) from exc

        if "error" in message:
            err = message["error"]
            if not isinstance(err, dict):
                raise ZBrushBridgeError(str(err))
            raise ZBrushBridgeError(
                str(err.get("message", err)),
                code=err.get("code") if isinstance(err.get("code"), int) else None,
                data=err.get("data") if isinstance(err.get("data"), dict) else None,
            )
        return message.get("result")

    def _payload(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        if self._token:
            payload["token"] = self._token
        return payload

    def _is_retryable_busy(self, exc: ZBrushBridgeError) -> bool:
        """True only for a refused-but-servable host.

        A ``blocked`` host is inside a native call and cannot be waited out, so
        it must never be retried: the hard constraint is that blocked verdicts
        are reported, not retried blind.
        """
        return exc.code == -32001 and bool((exc.data or {}).get("retryable"))

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = min(self._busy_backoff_sec * (2**attempt), self._busy_backoff_max_sec)
        if delay > 0:
            time.sleep(delay)

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = self.call("execute_python", code=code, context=context or {})
        if not isinstance(result, dict):
            raise ZBrushBridgeError(f"Unexpected execute_python result: {result!r}")
        return result

    def get_session_info(self) -> Dict[str, Any]:
        result = self.call("get_session_info")
        if not isinstance(result, dict):
            raise ZBrushBridgeError(f"Unexpected get_session_info result: {result!r}")
        return result

    def get_scene_info(self) -> Dict[str, Any]:
        result = self.call("get_scene_info")
        if not isinstance(result, dict):
            raise ZBrushBridgeError(f"Unexpected get_scene_info result: {result!r}")
        return result

    def _send(self, data: bytes, timeout: Optional[float] = None) -> bytes:
        # The timeout is a parameter, never instance state: probes and normal
        # calls run concurrently, and temporarily rewriting self._timeout would
        # let one path hand the other a 3-second deadline (or leak it for good).
        #
        # connect() stays outside the guarded block: a failure there proves no
        # byte reached the host. Anything from sendall onward is marked.
        sock = socket.create_connection(
            (self._host, self._port),
            timeout=self._timeout if timeout is None else timeout,
        )
        with sock:
            chunks: list[bytes] = []
            try:
                sock.sendall(data + b"\n")
                while True:
                    part = sock.recv(65536)
                    if not part:
                        break
                    chunks.append(part)
                    if b"\n" in part:
                        break
            except Exception as exc:
                setattr(exc, _POST_CONNECT_STAGE, True)
                raise
        return b"".join(chunks).split(b"\n", 1)[0]

    def __enter__(self) -> "SocketBridge":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()


# Backward-compatible alias from the pre-alpha HTTP scaffold.
ZBrushBridge = SocketBridge
