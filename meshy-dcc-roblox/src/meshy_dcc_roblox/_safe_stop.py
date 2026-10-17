"""Safe stop for a Studio that ``meshy-dcc start-instance`` launched.

Studio gives plugins no way to tell whether a place has unsaved changes, to
save it or to quit, so every stop counts as discarding unsaved work: it is
refused unless the caller passes ``discard_unsaved``, which the CLI sends only
after the user agreed. The sidecar then ends the Studio process it started.
Only a start-instance launch advertises ``safe_stop_url``.
"""

from __future__ import annotations

import os
import threading
from typing import Any

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"
KILL_AFTER_SECS = 15.0


def handle_stop_request(body: dict, server: Any) -> tuple:
    """Decide one stop request and, when allowed, end the launched Studio."""
    if not server.instance_id or body.get("instance_id") != server.instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    if body.get("discard_unsaved") is not True:
        return 409, {
            "stopping": False,
            "reason": "unsaved_changes",
            "detail": "Roblox Studio cannot report unsaved changes and a plugin cannot save "
            "a place. Ask the user to save it in Studio (File > Save to File, or Publish), "
            "then stop with --discard-unsaved once they agree that anything else is lost.",
        }
    studio = server.studio
    if studio is None or studio.poll() is not None:
        return 409, {
            "stopping": False,
            "reason": "host_refused",
            "detail": "This sidecar has no running Studio process to end (Studio may have "
            "opened the place in a process that was already running); close it in Studio.",
        }
    server.stop_requested.set()
    studio.terminate()
    threading.Thread(target=_kill_if_alive, args=(studio,), daemon=True).start()
    return 202, {"stopping": True}


def _kill_if_alive(studio: Any) -> None:
    try:
        studio.wait(timeout=KILL_AFTER_SECS)
    except Exception:  # noqa: BLE001 - subprocess.TimeoutExpired; the user agreed to discard
        studio.kill()


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop

    url = serve_safe_stop(lambda body: handle_stop_request(body, server))
    handle.update_gateway_metadata({"safe_stop_url": url})
