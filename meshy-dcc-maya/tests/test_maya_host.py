"""Tests for the MayaHost core HostAdapter implementation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SRC = Path(__file__).parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _install_maya(cmds):
    maya = MagicMock()
    maya.cmds = cmds
    return patch.dict(sys.modules, {"maya": maya, "maya.cmds": cmds})


class _Dispatcher:
    def __init__(self):
        self.shutdown_called = False

    def tick(self, _max_jobs):
        return MagicMock(more_pending=False)

    def is_shutdown(self):
        return self.shutdown_called

    def shutdown(self):
        self.shutdown_called = True


def test_is_background_uses_maya_batch_flag():
    from meshy_dcc_maya.host import MayaHost

    cmds = MagicMock()
    cmds.about.return_value = False
    with _install_maya(cmds):
        assert MayaHost(_Dispatcher()).is_background() is False
    cmds.about.assert_called_once_with(batch=True)


class _FakeTimer:
    """Stand-in for QTimer: records start() intervals; fire() delivers timeout."""

    def __init__(self):
        self.started = []
        self.stopped = False
        self.single_shot = None
        self._slots = []
        self.timeout = self

    def connect(self, slot):
        self._slots.append(slot)

    def setSingleShot(self, value):
        self.single_shot = value

    def start(self, msec):
        self.started.append(msec)

    def stop(self):
        self.stopped = True

    def fire(self):
        for slot in self._slots:
            slot()


def test_attach_tick_runs_the_tick_at_the_interval_it_returns(monkeypatch):
    # An idleEvent scriptJob ran the tick on every idle pass instead: Maya 2027
    # kept a core busy and never ran lowest-priority deferred work.
    from meshy_dcc_maya import host as host_module

    timer = _FakeTimer()
    monkeypatch.setattr(host_module, "_qtimer_class", lambda: lambda: timer)
    host = host_module.MayaHost(_Dispatcher())
    tick = MagicMock(side_effect=[0.0, 0.5, None])
    host.attach_tick(tick)
    host.attach_tick(tick)  # already attached: no second timer
    for _ in range(3):
        timer.fire()

    assert timer.single_shot is True
    assert timer.started == [0, 0, 500]  # first run, then each returned interval
    assert tick.call_count == 3
    assert host._timer is None  # None stops the timer


def test_detach_tick_stops_the_timer_and_is_idempotent(monkeypatch):
    from meshy_dcc_maya import host as host_module

    timer = _FakeTimer()
    monkeypatch.setattr(host_module, "_qtimer_class", lambda: lambda: timer)
    host = host_module.MayaHost(_Dispatcher())
    tick = MagicMock(return_value=0.5)
    host.attach_tick(tick)
    host.detach_tick()
    host.detach_tick()
    timer.fire()  # a timeout already queued at detach does nothing

    assert timer.stopped is True
    tick.assert_not_called()
    assert host._timer is None


def test_callable_dispatcher_forwards_core_metadata():
    from meshy_dcc_maya.host import MayaCallableDispatcher

    dispatcher = MagicMock()
    bridge = MayaCallableDispatcher(dispatcher)
    fn = MagicMock(return_value={"ok": True})

    context = object()
    result = bridge.dispatch_callable(fn, affinity="main", action_name="maya__tool", context=context)

    assert result == {"ok": True}
    fn.assert_called_once_with(affinity="main", action_name="maya__tool", context=context)
    dispatcher.post.assert_not_called()
