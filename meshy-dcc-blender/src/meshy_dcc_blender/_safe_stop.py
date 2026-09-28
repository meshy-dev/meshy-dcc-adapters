"""Safe stop for Blender hosts launched by ``meshy-dcc start-instance``.

Blender's dirty flag misses edits made through Python, so a stop cannot tell
whether work is unsaved. The stop is refused unless the caller passes
``discard_unsaved``, which the CLI sends only after the user agreed to lose
unsaved changes. Only a start-instance launch advertises ``safe_stop_url``;
a Blender the user opened themselves is never stopped this way.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


def _quit_blender() -> None:
    import bpy  # noqa: PLC0415 - only importable inside Blender

    bpy.ops.wm.quit_blender()


def handle_stop_request(body: dict, instance_id: Any, schedule_quit: Any) -> tuple:
    """Decide one stop request; ``schedule_quit`` runs the quit on the main thread."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    if body.get("discard_unsaved") is not True:
        return 409, {
            "stopping": False,
            "reason": "unsaved_state_unknown",
            "detail": "Blender cannot tell whether work is unsaved. Save what should be kept, then "
            "stop with --discard-unsaved once the user agrees to lose the rest.",
        }
    schedule_quit()
    return 202, {"stopping": True}


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a started start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    try:
        import bpy  # noqa: PLC0415
        from meshy_dcc_core.host.safe_stop import serve_safe_stop  # noqa: PLC0415
    except ImportError as exc:
        logger.debug("safe stop unavailable: %s", exc)
        return

    def schedule_quit() -> None:
        bpy.app.timers.register(_quit_blender, first_interval=0.1)

    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, schedule_quit))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
