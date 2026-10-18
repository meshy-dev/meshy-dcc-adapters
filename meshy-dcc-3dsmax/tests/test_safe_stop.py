"""3ds Max safe stop refuses unless the user agreed to discard unsaved work."""

from types import SimpleNamespace

from meshy_dcc_3dsmax import _safe_stop
from meshy_dcc_3dsmax._safe_stop import handle_stop_request


def test_stop_needs_matching_instance_and_discard_consent():
    quits = []

    def decide(body):
        return handle_stop_request(body, "inst-1", lambda: quits.append(1))

    assert decide({"instance_id": "inst-2", "discard_unsaved": True})[1]["reason"] == "instance_mismatch"
    status, reply = decide({"instance_id": "inst-1"})
    assert (status, reply["reason"]) == (409, "unsaved_state_unknown")
    assert quits == []
    assert decide({"instance_id": "inst-1", "discard_unsaved": True}) == (202, {"stopping": True})
    assert quits == [1]


def test_only_a_start_instance_launch_advertises_and_quits_through_the_main_thread_queue(monkeypatch):
    published, posted, pokes = [], [], []
    handle = SimpleNamespace(update_gateway_metadata=published.append)
    queue = SimpleNamespace(post=posted.append)
    dispatcher = SimpleNamespace(host_dispatcher=queue, poke_host_pump=lambda: pokes.append(1))
    server = SimpleNamespace(_handle=handle, _max_dispatcher=dispatcher, instance_id="inst-1")
    handlers = []
    import meshy_dcc_core.host.safe_stop as core_safe_stop

    monkeypatch.setattr(core_safe_stop, "serve_safe_stop", lambda h: handlers.append(h) or "http://127.0.0.1:1/safe-stop")

    monkeypatch.delenv(_safe_stop.START_OPERATION_ENV, raising=False)
    _safe_stop.attach_safe_stop(server)
    assert published == []

    monkeypatch.setenv(_safe_stop.START_OPERATION_ENV, "op-1")
    _safe_stop.attach_safe_stop(server)
    assert published == [{"safe_stop_url": "http://127.0.0.1:1/safe-stop"}]
    assert handlers[0]({"instance_id": "inst-1", "discard_unsaved": True})[0] == 202
    assert posted == [_safe_stop._quit_max] and pokes == [1]


def test_pump_is_poked_only_from_the_thread_that_owns_its_timer():
    import threading

    from meshy_dcc_3dsmax.dispatcher.ui import MaxUiDispatcher

    pokes = []
    dispatcher = MaxUiDispatcher()
    dispatcher.attach_pump_controller(SimpleNamespace(schedule_soon=lambda: pokes.append(1)))

    # The safe-stop request arrives on a server thread.
    other = threading.Thread(target=dispatcher.poke_host_pump)
    other.start()
    other.join()
    assert pokes == []

    dispatcher.poke_host_pump()
    assert pokes == [1]
