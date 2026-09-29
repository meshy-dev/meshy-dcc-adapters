"""Safe stop for Unity Editors launched by ``meshy-dcc start-instance``.

Unity knows whether its open scenes are dirty, so a stop proceeds when every
scene is saved and is refused otherwise, unless the caller passes
``discard_unsaved``, which the CLI sends only after the user agreed to lose
unsaved changes. Only a start-instance launch advertises ``safe_stop_url``;
an Editor the user opened themselves is never stopped this way.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


def handle_stop_request(
    body: dict, instance_id: Any, call_host: Callable[..., dict]
) -> tuple[int, dict]:
    """Decide one stop request and, when allowed, ask the Editor to exit."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    discard = body.get("discard_unsaved") is True
    try:
        session = call_host("meshy.session")
        if session.get("dirty") and not discard:
            return 409, {
                "stopping": False,
                "reason": "unsaved_changes",
                "detail": "Unity has unsaved scenes. Save what should be kept, then stop with "
                "--discard-unsaved once the user agrees to lose the rest.",
            }
        call_host(
            "meshy.session.quit",
            {
                "expected_pid": session["host_pid"],
                "workspace": session["workspace"],
                "discard_unsaved": discard,
            },
        )
    except Exception as exc:  # noqa: BLE001 - report the Editor's refusal, never guess
        return 409, {"stopping": False, "reason": "host_refused", "detail": str(exc)}
    return 202, {"stopping": True}


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop

    from .bridge import call_host

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, call_host))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
