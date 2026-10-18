"""Maya host adapter for meshy-dcc-core host dispatchers."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Callable, Optional

# Import third-party modules
from meshy_dcc_core.host import HostAdapter

from meshy_dcc_maya.api import require_main_thread


class MayaCallableDispatcher:
    """Callable bridge used after native core dispatcher attachment.

    ``McpHttpServer.attach_dispatcher`` owns the native dispatcher hop.
    This bridge lets ``HostExecutionBridge`` share that same route for
    in-process skill execution; the callable is already running on the
    host-dispatched thread when it reaches this point.
    """

    def __init__(self, dispatcher: Any) -> None:
        self._dispatcher = dispatcher

    def dispatch_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    def shutdown(self, reason: str = "Interrupted") -> Any:
        _ = reason
        return self._dispatcher.shutdown()


def _qtimer_class() -> Any:
    try:
        from PySide6.QtCore import QTimer  # noqa: PLC0415
    except ImportError:
        from PySide2.QtCore import QTimer  # noqa: PLC0415
    return QTimer


class MayaHost(HostAdapter):
    """Drive a core host dispatcher from a Qt timer on Maya's main thread.

    The timer honours the interval each tick returns (0 s with work queued,
    the idle interval otherwise). An ``idleEvent`` scriptJob fired on every
    idle pass instead: one core stayed busy for as long as Maya ran, and Maya
    never went idle, so ``evalDeferred(..., lowestPriority=True)`` work, safe
    stop's quit among it, never ran (Maya 2027).
    """

    def __init__(self, dispatcher: Any, **kwargs: Any) -> None:
        kwargs.setdefault("name", "maya-host")
        super().__init__(dispatcher, **kwargs)
        self._timer: Any = None

    @require_main_thread
    def is_background(self) -> bool:
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            return bool(cmds.about(batch=True))
        except ImportError:
            return True

    @require_main_thread
    def attach_tick(self, tick_fn: Callable[[], Optional[float]]) -> None:
        if self._timer is not None:
            return
        timer = _qtimer_class()()
        timer.setSingleShot(True)

        def _fire() -> None:
            if self._timer is not timer:
                return
            interval = tick_fn()
            if interval is None:
                self._timer = None
                return
            timer.start(max(0, int(interval * 1000)))

        timer.timeout.connect(_fire)
        self._timer = timer
        timer.start(0)

    @require_main_thread
    def detach_tick(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.stop()
