"""The main-thread dispatch budget is configurable and composes with per-call limits."""

from __future__ import annotations

import sys
import threading
from unittest.mock import patch

import pytest

from meshy_dcc_blender import _env
from meshy_dcc_blender.dispatcher import create_dispatcher
from meshy_dcc_blender.host import BlenderUiDispatcher
from meshy_dcc_blender.server import BlenderMcpServer, BlenderServerOptions
from tests.test_host_adapter import _mock_bpy


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(_env.ENV_MAIN_THREAD_TIMEOUT_MS, raising=False)


def test_default_budget_is_thirty_seconds():
    assert _env.resolve_main_thread_timeout_ms() == 30_000
    assert BlenderUiDispatcher().timeout_ms == 30_000
    assert create_dispatcher(ui_mode=False).timeout_ms == 30_000


def test_explicit_budget_beats_the_environment(monkeypatch):
    monkeypatch.setenv(_env.ENV_MAIN_THREAD_TIMEOUT_MS, "90000")
    assert _env.resolve_main_thread_timeout_ms() == 90_000
    assert _env.resolve_main_thread_timeout_ms(120_000) == 120_000


@pytest.mark.parametrize("raw", ["", "abc", "0", "-5", "1.5"])
def test_an_invalid_environment_value_falls_back_to_the_default(monkeypatch, raw):
    monkeypatch.setenv(_env.ENV_MAIN_THREAD_TIMEOUT_MS, raw)
    assert _env.resolve_main_thread_timeout_ms() == 30_000


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "30000"])
def test_an_invalid_explicit_budget_is_rejected(value):
    with pytest.raises(ValueError, match="main_thread_timeout_ms"):
        _env.resolve_main_thread_timeout_ms(value)
    with pytest.raises(ValueError, match="main_thread_timeout_ms"):
        BlenderServerOptions(main_thread_timeout_ms=value)


def test_the_server_builds_its_default_dispatcher_with_the_budget(monkeypatch):
    server = BlenderMcpServer(port=0, main_thread_timeout_ms=45_000)
    assert server._pump_dispatcher.timeout_ms == 45_000

    monkeypatch.setenv(_env.ENV_MAIN_THREAD_TIMEOUT_MS, "60000")
    assert BlenderMcpServer(port=0)._pump_dispatcher.timeout_ms == 60_000
    options = BlenderServerOptions(port=0, main_thread_timeout_ms=15_000)
    assert BlenderMcpServer(options=options)._pump_dispatcher.timeout_ms == 15_000
    assert options.dispatcher is None, "the caller's options must not be mutated"


def test_a_caller_supplied_dispatcher_keeps_its_own_budget():
    dispatcher = BlenderUiDispatcher(timeout_ms=5_000)
    server = BlenderMcpServer(port=0, dispatcher=dispatcher, main_thread_timeout_ms=90_000)
    assert server._pump_dispatcher is dispatcher
    assert dispatcher.timeout_ms == 5_000


def test_the_keyword_cannot_be_dropped_silently_next_to_options():
    with pytest.raises(ValueError, match="BlenderServerOptions"):
        BlenderMcpServer(options=BlenderServerOptions(port=0), main_thread_timeout_ms=1_000)


def test_a_per_tool_hint_wins_and_the_budget_is_only_the_fallback():
    dispatcher = BlenderUiDispatcher(timeout_ms=90_000)
    assert dispatcher._timeout_ms_from_hint(None) == 90_000
    assert dispatcher._timeout_ms_from_hint(0) == 90_000
    assert dispatcher._timeout_ms_from_hint(7) == 7_000


def test_the_budget_ends_a_main_thread_call_that_never_starts():
    """On the Python route a call that cannot start is dropped when the budget runs out."""
    bpy, _registered = _mock_bpy()
    outcome = []

    with patch.dict(sys.modules, {"bpy": bpy}):
        dispatcher = BlenderUiDispatcher(timeout_ms=50)

        def call():
            try:
                dispatcher.dispatch_callable(lambda: "late", action_name="slow")
            except RuntimeError as exc:
                outcome.append(str(exc))

        worker = threading.Thread(target=call)
        worker.start()
        worker.join(timeout=5)  # the fake timer is never ticked, so the queue is never drained

    assert not worker.is_alive()
    assert outcome, "the call must fail instead of hanging forever"
