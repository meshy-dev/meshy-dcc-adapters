"""Safe stop for 3ds Max sessions launched by ``meshy-dcc start-instance``.

``quitMax #noPrompt`` exits without asking to save. Whether 3ds Max's own
dirty flag (``getSaveRequired()``) sees every edit made through ``pymxs`` has
not been checked on a real host, so the stop is refused unless the caller
passes ``discard_unsaved``, which the CLI sends only after the user agreed to
lose unsaved changes. Only a start-instance launch advertises
``safe_stop_url``; a 3ds Max the user opened themselves is never stopped this
way.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


def _quit_max() -> None:
    import pymxs  # noqa: PLC0415 - only importable inside 3ds Max

    rt = pymxs.runtime
    rt.quitMax(rt.Name("noPrompt"))


def handle_stop_request(body: dict, instance_id: Any, schedule_quit: Callable[[], None]) -> tuple:
    """Decide one stop request; ``schedule_quit`` runs the quit on the main thread."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    if body.get("discard_unsaved") is not True:
        return 409, {
            "stopping": False,
            "reason": "unsaved_state_unknown",
            "detail": "3ds Max quits without asking to save. Save what should be kept (save_scene), "
            "then stop with --discard-unsaved once the user agrees to lose the rest.",
        }
    schedule_quit()
    return 202, {"stopping": True}


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if server is None or not os.environ.get(START_OPERATION_ENV):
        return
    handle = getattr(server, "_handle", None)
    dispatcher = getattr(server, "_max_dispatcher", None)
    host_queue = getattr(dispatcher, "host_dispatcher", None)
    if handle is None or host_queue is None:
        logger.debug("safe stop unavailable: no server handle or main-thread queue")
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop  # noqa: PLC0415

    def schedule_quit() -> None:
        # The same queue the Qt pump drains for tool calls: one consumer, on the main thread.
        host_queue.post(_quit_max)
        poke = getattr(dispatcher, "poke_host_pump", None)
        if callable(poke):
            poke()

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, schedule_quit))
    # Reaches the registry row on the next heartbeat.
    handle.update_gateway_metadata({"safe_stop_url": url})
