"""Safe stop for Painter instances launched by ``meshy-dcc start-instance``.

``substance_painter.application.close()`` closes Painter; its unsaved-work
behaviour has not been checked on a real host, so the stop reads the project
state first and refuses while the open project needs saving, or when Painter
cannot tell, unless the request carries ``discard_unsaved``, which the CLI
sends only after the user agreed to lose unsaved work. Only a start-instance
launch advertises ``safe_stop_url``; a Painter the user opened themselves is
never stopped this way.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"
QUIT_DELAY_MS = 200


def unsaved_projects(project: Any) -> Optional[List[str]]:
    """The open project when it needs saving, ``[]`` when nothing is unsaved, None when Painter cannot tell."""
    try:
        if not project.is_open():
            return []
        if not project.needs_saving():
            return []
        return [str(project.file_path() or project.name() or "untitled project")]
    except Exception as exc:  # noqa: BLE001 - unknown state must read as unsaved
        logger.debug("project state readback failed: %s", exc)
        return None


def stop_if_saved(project: Any, discard_unsaved: bool, quit_later: Callable[[], None]) -> Optional[List[str]]:
    """On Painter's main thread: schedule the quit unless something is unsaved; returns what blocked it."""
    unsaved = unsaved_projects(project)
    if not discard_unsaved and unsaved != []:
        return unsaved
    quit_later()
    return []


def handle_stop_request(body: dict, instance_id: Any, run_on_main: Callable[[bool], Optional[List[str]]]) -> tuple:
    """Decide one stop request; ``run_on_main`` runs ``stop_if_saved`` on Painter's main thread."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    blocked = run_on_main(body.get("discard_unsaved") is True)
    if blocked != []:
        return 409, {
            "stopping": False,
            "reason": "unsaved_changes",
            "unsaved": blocked,
            "detail": "The Painter project has unsaved changes, or Painter cannot tell. Save what should be "
            "kept, then stop with --discard-unsaved once the user agrees to lose the rest.",
        }
    return 202, {"stopping": True}


def attach_safe_stop(server: Any, dispatcher: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    try:
        import substance_painter.application as application  # noqa: PLC0415 - Painter only
        import substance_painter.project as project  # noqa: PLC0415
        from meshy_dcc_core.host.safe_stop import serve_safe_stop  # noqa: PLC0415
    except ImportError as exc:
        logger.debug("safe stop unavailable: %s", exc)
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    try:
        from PySide6.QtCore import QTimer  # noqa: PLC0415 - Painter 10.1+
    except ImportError:
        from PySide2.QtCore import QTimer  # noqa: PLC0415 - older Painter

    def quit_later() -> None:
        # Let the stop reply leave before Painter starts closing.
        QTimer.singleShot(QUIT_DELAY_MS, application.close)

    def run_on_main(discard: bool) -> Optional[List[str]]:
        return dispatcher.dispatch_callable(
            stop_if_saved, project, discard, quit_later, affinity="main", timeout_hint_secs=30
        )

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, run_on_main))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
