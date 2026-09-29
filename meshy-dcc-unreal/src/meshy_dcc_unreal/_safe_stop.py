"""Safe stop for Unreal editors launched by ``meshy-dcc start-instance``.

``unreal.SystemLibrary.quit_editor`` exits without asking to save, so the stop
checks for unsaved maps and assets first and refuses while there are any,
unless the request carries ``discard_unsaved``, which the CLI sends only after
the user agreed to lose them. An editor that cannot report unsaved state
counts as unsaved. Only a start-instance launch advertises ``safe_stop_url``;
an editor the user opened themselves is never stopped this way.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"


_engine_mounts: Optional[Tuple[str, ...]] = None


def engine_mounts(unreal: Any) -> Tuple[str, ...]:
    """Content roots that belong to the engine install: /Engine/ and engine plugins' mounts."""
    global _engine_mounts
    if _engine_mounts is None:
        mounts = ["/Engine/"]
        try:
            full = unreal.Paths.convert_relative_path_to_full
            engine = os.path.realpath(full(unreal.Paths.engine_dir())) + os.sep
            library = unreal.PluginBlueprintLibrary
            for name in library.get_enabled_plugin_names():
                mount = library.get_plugin_mounted_asset_path(name)
                base = library.get_plugin_base_dir(name)
                if mount and base and os.path.realpath(full(base)).startswith(engine):
                    mounts.append(str(mount).rstrip("/") + "/")
        except Exception as exc:  # noqa: BLE001 - without the list, every package counts as the user's
            logger.debug("engine plugin mounts unavailable: %s", exc)
        _engine_mounts = tuple(mounts)
    return _engine_mounts


def dirty_packages(unreal: Any) -> Optional[Tuple[List[str], List[str]]]:
    """Dirty map and content packages as (project, engine), or None when the editor cannot tell.

    Engine packages get dirty on their own, for example when a material gains a usage flag.
    They are no one's unsaved work and must never be saved into the engine install.
    """
    try:
        utils = unreal.EditorLoadingAndSavingUtils
        packages = list(utils.get_dirty_map_packages()) + list(utils.get_dirty_content_packages())
        names = sorted({str(package.get_name()) for package in packages})
    except Exception as exc:  # noqa: BLE001 - unknown state must read as unsaved
        logger.debug("dirty package readback failed: %s", exc)
        return None
    engine = engine_mounts(unreal)
    owned_by_engine = [name for name in names if (name + "/").startswith(engine)]
    return [name for name in names if name not in owned_by_engine], owned_by_engine


def unsaved_packages(unreal: Any) -> Optional[List[str]]:
    """The project's dirty packages, or None when the editor cannot tell."""
    dirty = dirty_packages(unreal)
    return None if dirty is None else dirty[0]


def stop_if_saved(unreal: Any, discard_unsaved: bool) -> Optional[List[str]]:
    """On the editor thread: quit unless something is unsaved; returns what blocked the quit."""
    unsaved = unsaved_packages(unreal)
    if not discard_unsaved and unsaved != []:
        return unsaved
    unreal.SystemLibrary.quit_editor()
    return []


def handle_stop_request(body: dict, instance_id: Any, run_on_editor: Callable[[bool], Optional[List[str]]]) -> tuple:
    """Decide one stop request; ``run_on_editor`` runs ``stop_if_saved`` on the editor thread."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    blocked = run_on_editor(body.get("discard_unsaved") is True)
    if blocked != []:
        return 409, {
            "stopping": False,
            "reason": "unsaved_changes",
            "unsaved": blocked,
            "detail": "Unreal has unsaved maps or assets, or cannot tell. Save what should be kept, then stop "
            "with --discard-unsaved once the user agrees to lose the rest.",
        }
    return 202, {"stopping": True}


def attach_safe_stop(server: Any) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    try:
        import unreal  # noqa: PLC0415
        from meshy_dcc_core.host.safe_stop import serve_safe_stop  # noqa: PLC0415
    except ImportError as exc:
        logger.debug("safe stop unavailable: %s", exc)
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    dispatcher = server._main_thread_dispatcher

    def run_on_editor(discard: bool) -> Optional[List[str]]:
        return dispatcher.dispatch_callable(stop_if_saved, unreal, discard, affinity="main", timeout_hint_secs=30)

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id, run_on_editor))
    # Reaches the registry row on the next heartbeat (within about 5 s).
    handle.update_gateway_metadata({"safe_stop_url": url})
