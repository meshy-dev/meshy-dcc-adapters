"""Safe stop for Houdini sessions launched by ``meshy-dcc start-instance``.

The stop reads Houdini's dirty flag on the main thread and refuses while the
scene has unsaved changes, or while Houdini cannot tell, unless the request
carries ``discard_unsaved``, which the CLI sends only after the user agreed to
lose them. It then quits through ``hou.exit(suppress_save_prompt=True)`` from
a deferred main-thread call, so the reply is sent before Houdini goes away.
Only a start-instance launch advertises ``safe_stop_url``; a Houdini the user
opened themselves is never stopped this way.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from meshy_dcc_houdini._hip_file_state import get_hip_dirty_state

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


def stop_if_saved(hou: Any, discard_unsaved: bool, schedule_exit: Callable[[], None]) -> Optional[str]:
    """On the main thread: schedule the exit, or return why it was refused."""
    dirty = get_hip_dirty_state(hou)
    if dirty is not False and not discard_unsaved:
        return "unsaved_changes" if dirty else "unsaved_state_unknown"
    schedule_exit()
    return None


def handle_stop_request(body: dict, instance_id: Any, run_on_main: Callable[[bool], Optional[str]]) -> tuple:
    """Decide one stop request; ``run_on_main`` runs ``stop_if_saved`` on Houdini's main thread."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    refused = run_on_main(body.get("discard_unsaved") is True)
    if refused:
        return 409, {
            "stopping": False,
            "reason": refused,
            "detail": "Houdini has unsaved changes, or cannot tell. Save what should be kept, then stop "
            "with --discard-unsaved once the user agrees to lose the rest.",
        }
    return 202, {"stopping": True}


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    try:
        import hdefereval  # noqa: PLC0415 - only importable inside Houdini
        import hou  # noqa: PLC0415
        from meshy_dcc_core.host.safe_stop import serve_safe_stop  # noqa: PLC0415
    except ImportError as exc:
        logger.debug("safe stop unavailable: %s", exc)
        return
    handle = getattr(server, "_handle", None)
    if handle is None or not hou.isUIAvailable():
        return
    dispatcher = server._houdini_dispatcher

    def schedule_exit() -> None:
        hdefereval.executeDeferred(lambda: hou.exit(exit_code=0, suppress_save_prompt=True))

    def run_on_main(discard: bool) -> Optional[str]:
        return dispatcher.dispatch_callable(
            stop_if_saved, hou, discard, schedule_exit, affinity="main", timeout_hint_secs=30
        )

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, run_on_main))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
