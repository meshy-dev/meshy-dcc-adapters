import pytest

from meshy_dcc_godot.server import GodotMcpServer


def test_server_wires_http_main_affinity_dispatcher():
    server = GodotMcpServer(port=0)
    try:
        assert server._execution_bridge.resolve_host_dispatcher() is server._host_dispatcher
    finally:
        server.stop()


def test_server_starts_with_disconnected_godot_bridge_not_ready():
    server = GodotMcpServer(port=0)
    try:
        report = server._readiness_binder.report_subset()
        assert report["process"] is True
        assert report["skill_catalog"] is True
        assert report["dcc"] is False
        assert report["host_execution_bridge"] is False
        assert report["main_thread_executor"] is False
    finally:
        server.stop()


def test_server_context_publisher_routes_typed_editor_snapshot_to_core(monkeypatch):
    from meshy_dcc_godot import server as server_module

    published = []
    monkeypatch.setattr(
        server_module,
        "call_host",
        lambda method: {
            "version": "4.4.1.stable",
            "display_name": "Server Context Test",
            "scene": "res://main.tscn",
            "documents": ["res://main.tscn"],
        },
        raising=False,
    )
    monkeypatch.setattr(
        server_module.GodotMcpServer,
        "update_gateway_metadata",
        lambda self, **context: published.append(context) or True,
    )

    server = server_module.GodotMcpServer(port=0)
    try:
        assert server._context_publisher.refresh() is True
    finally:
        server.stop()

    assert published == [
        {
            "version": "4.4.1.stable",
            "display_name": "Server Context Test",
            "scene": "res://main.tscn",
            "documents": ["res://main.tscn"],
        }
    ]


def test_start_server_defers_port_resolution_to_core(monkeypatch):
    from types import SimpleNamespace

    from meshy_dcc_godot import server as server_module

    ports = []
    stub = SimpleNamespace(
        is_running=False,
        register_builtin_actions=lambda: None,
        start=lambda: None,
        stop=lambda: None,
    )

    monkeypatch.setattr(server_module, "_server", None)
    monkeypatch.setattr(
        server_module,
        "GodotMcpServer",
        lambda port=None, **kwargs: ports.append(port) or stub,
    )
    monkeypatch.setenv("MESHY_DCC_GODOT_PORT", "8765")

    server_module.start_server(0)
    server_module.stop_server()
    server_module.start_server()
    server_module.stop_server()

    assert ports == [0, None]


@pytest.mark.parametrize("dcc_pid", [None, 424242])
def test_server_publishes_only_an_explicit_editor_pid(dcc_pid):
    server = GodotMcpServer(port=0, dcc_pid=dcc_pid)
    try:
        assert server._options.diagnostics.dcc_pid == dcc_pid
        assert server._config.host_pid == dcc_pid
    finally:
        server.stop()


def test_start_server_passes_the_editor_pid_to_the_real_constructor(monkeypatch):
    from meshy_dcc_godot import server as server_module

    monkeypatch.setattr(server_module, "_server", None)
    monkeypatch.setattr(GodotMcpServer, "register_builtin_actions", lambda self: None)
    monkeypatch.setattr(GodotMcpServer, "start", lambda self: None)
    server = server_module.start_server(port=0, dcc_pid=424242)
    try:
        assert server._config.host_pid == 424242
    finally:
        server_module.stop_server()


@pytest.mark.parametrize("watch_pid", [None, 424242])
def test_main_uses_the_watched_editor_as_the_core_host_pid(monkeypatch, watch_pid):
    from types import SimpleNamespace

    from meshy_dcc_godot import server as server_module

    calls = []
    stopped = SimpleNamespace(wait=lambda: True, set=lambda: None)
    monkeypatch.setattr(
        server_module,
        "start_server",
        lambda **kwargs: calls.append(("start", kwargs)),
    )
    monkeypatch.setattr(server_module, "stop_server", lambda: calls.append(("stop",)))
    watchers = []
    monkeypatch.setattr(
        server_module,
        "threading",
        SimpleNamespace(
            Event=lambda: stopped,
            Thread=lambda **kwargs: SimpleNamespace(start=lambda: watchers.append(kwargs)),
        ),
    )
    monkeypatch.setattr(
        server_module,
        "signal",
        SimpleNamespace(SIGINT=2, SIGTERM=15, signal=lambda *args: None),
    )

    server_module.main(watch_pid=watch_pid)

    assert calls == [("start", {"dcc_pid": watch_pid}), ("stop",)]
    assert len(watchers) == (1 if watch_pid else 0)
    if watch_pid:
        assert watchers[0]["target"] is server_module._watch_host
        assert watchers[0]["args"] == (watch_pid, stopped)
