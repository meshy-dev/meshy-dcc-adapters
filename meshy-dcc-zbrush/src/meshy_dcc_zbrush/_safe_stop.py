"""Safe stop for ZBrush instances launched by ``meshy-dcc start-instance``.

The ZBrush Python SDK cannot tell whether the open project or tools have
unsaved changes, so every stop counts as one that may lose work: it is refused
unless the caller passes ``discard_unsaved``, which the CLI sends only after
the user agreed to lose what is not saved. An agreed stop terminates the ZBrush
process the sidecar watches. Only a start-instance launch advertises
``safe_stop_url``; a ZBrush the user opened themselves is never stopped this way.
"""

from __future__ import annotations

import os
import signal
from typing import Any, Callable

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


def _terminate(pid: int) -> None:
    # SIGTERM; on Windows os.kill ends the process with TerminateProcess.
    os.kill(pid, signal.SIGTERM)


def handle_stop_request(
    body: dict, instance_id: Any, host_pid: int, terminate: Callable[[int], None] = _terminate
) -> tuple[int, dict]:
    """Decide one stop request and, when the user agreed to discard, end ZBrush."""
    if not instance_id or body.get("instance_id") != str(instance_id):
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    if body.get("discard_unsaved") is not True:
        return 409, {
            "stopping": False,
            "reason": "unsaved_changes",
            "detail": "ZBrush cannot report unsaved changes. Save what should be kept "
            "(zbrush-file save_project or save_tool), then stop with --discard-unsaved "
            "once the user agrees to lose the rest.",
        }
    try:
        terminate(host_pid)
    except OSError as exc:
        return 409, {"stopping": False, "reason": "host_refused", "detail": str(exc)}
    return 202, {"stopping": True}


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    host_pid = int(getattr(server, "dcc_pid", 0) or 0)
    if not os.environ.get(START_OPERATION_ENV) or host_pid in (0, os.getpid()):
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, host_pid))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
