"""Safe stop for Maya sessions launched by ``meshy-dcc start-instance``.

``cmds.quit(force=True)`` exits without asking to save, so the stop reads
Maya's scene-modified flag on the main thread first and refuses while the
scene has unsaved changes, unless the request carries ``discard_unsaved``,
which the CLI sends only after the user agreed to lose them. A Maya that does
not answer in time counts as unsaved. Only a start-instance launch advertises
``safe_stop_url``; a Maya the user opened themselves is never stopped this way.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"
MAIN_THREAD_TIMEOUT_SECS = 30.0


def stop_if_saved(cmds: Any, discard_unsaved: bool) -> bool:
    """On Maya's main thread: schedule the quit unless the scene is modified; True when quitting."""
    if not discard_unsaved and cmds.file(query=True, modified=True):
        return False
    # Deferred, so the HTTP reply leaves before Maya starts to exit.
    cmds.evalDeferred(lambda: cmds.quit(force=True), lowestPriority=True)
    return True


def handle_stop_request(body: dict, instance_id: Any, run_on_main: Callable[[bool], bool]) -> tuple:
    """Decide one stop request; ``run_on_main`` runs ``stop_if_saved`` on Maya's main thread."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    try:
        stopping = run_on_main(body.get("discard_unsaved") is True)
    except Exception as exc:  # noqa: BLE001 - an unanswered check must read as unsaved
        return 409, {
            "stopping": False,
            "reason": "unsaved_state_unknown",
            "detail": "Maya did not report whether the scene is saved ({}). Save what should be kept, "
            "then stop with --discard-unsaved once the user agrees to lose the rest.".format(exc),
        }
    if not stopping:
        return 409, {
            "stopping": False,
            "reason": "unsaved_changes",
            "detail": "The Maya scene has unsaved changes. Save what should be kept, then stop with "
            "--discard-unsaved once the user agrees to lose the rest.",
        }
    return 202, {"stopping": True}


def run_on_main_thread(func: Callable[[], bool], timeout: float = MAIN_THREAD_TIMEOUT_SECS) -> bool:
    """Run ``func`` through ``maya.utils.executeInMainThreadWithResult`` with a deadline.

    A call that misses the deadline is cancelled: if Maya's main thread picks
    it up later, it does nothing, so a stop reported as refused never quits.
    """
    import maya.utils  # noqa: PLC0415 - only importable inside Maya

    cancelled = threading.Event()
    done = threading.Event()
    outcome: dict = {}

    def guarded() -> bool:
        return False if cancelled.is_set() else func()

    def call() -> None:
        try:
            outcome["value"] = maya.utils.executeInMainThreadWithResult(guarded)
        except BaseException as exc:  # noqa: BLE001 - handed back to the caller
            outcome["error"] = exc
        finally:
            done.set()

    threading.Thread(target=call, name="meshy-dcc-safe-stop-check", daemon=True).start()
    if not done.wait(timeout):
        cancelled.set()
        raise TimeoutError("no answer from Maya's main thread in {:.0f} s".format(timeout))
    if "error" in outcome:
        raise outcome["error"]
    return bool(outcome["value"])


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    try:
        import maya.cmds as cmds  # noqa: PLC0415
        from meshy_dcc_core.host.safe_stop import serve_safe_stop  # noqa: PLC0415
    except ImportError as exc:
        logger.debug("safe stop unavailable: %s", exc)
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return

    def run_on_main(discard: bool) -> bool:
        return run_on_main_thread(lambda: stop_if_saved(cmds, discard))

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, run_on_main))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
