"""3ds Max in-process skill executor.

Core 0.17 routes embedded adapter skills through ``HostExecutionBridge``.
This module keeps the 3ds Max script convention local: skill scripts expose
``main(**params)`` and return plain dictionaries.
"""

from __future__ import annotations

import contextlib
import functools
import logging
import threading
from pathlib import Path
from typing import Any, ContextManager, Dict, Iterator, Mapping

from meshy_dcc_core import parse_skill_md
from meshy_dcc_core.skill import skill_exception

logger = logging.getLogger(__name__)

_busy_lock = threading.Lock()
_busy_count = 0


@contextlib.contextmanager
def _busy_scope() -> Iterator[None]:
    global _busy_count
    with _busy_lock:
        _busy_count += 1
    try:
        yield
    finally:
        with _busy_lock:
            _busy_count = max(0, _busy_count - 1)


def is_busy() -> bool:
    """Return ``True`` while a 3ds Max skill script is executing."""
    with _busy_lock:
        return _busy_count > 0


@functools.lru_cache(maxsize=None)
def _is_read_only(script_path: str) -> bool:
    """Whether the tool that runs this script is declared ``read_only``."""
    path = Path(script_path)
    try:
        skill = parse_skill_md(str(path.parent))
    except Exception:  # noqa: BLE001
        return False
    return any(tool.source_file == path.name and tool.read_only for tool in getattr(skill, "tools", None) or ())


def _scene_edit(script_path: str) -> ContextManager[Any]:
    """Record a writing tool in 3ds Max's undo.

    pymxs runs with undo off, and 3ds Max then never marks the scene as
    modified: an edit made by a tool would look saved, and opening another
    scene would drop it without asking. An undo record sets that flag (and lets
    the user undo the tool). Read-only tools stay outside, since accepting even
    an empty record marks the scene modified.
    """
    try:
        import pymxs  # noqa: PLC0415 - only importable inside 3ds Max
    except ImportError:
        return contextlib.nullcontext()
    undo = getattr(pymxs, "undo", None)
    if undo is None or _is_read_only(script_path):
        return contextlib.nullcontext()
    return undo(True, "Meshy: {}".format(Path(script_path).stem))


def run_skill_script(script_path: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    """Load and execute a 3ds Max skill script in-process."""
    with _busy_scope():
        return _run_skill_script_untracked(script_path, dict(params))


def _run_skill_script_untracked(script_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415
    import uuid  # noqa: PLC0415

    path = Path(script_path)
    if not path.is_file():
        return {"success": False, "message": "Skill script not found: {}".format(script_path)}

    mod_name = "_meshy_dcc_3dsmax_skill_{}".format(uuid.uuid4().hex)
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        return {"success": False, "message": "Cannot load skill script: {}".format(script_path)}

    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            return skill_exception(exc, message="Error loading skill script: {}".format(script_path))

        try:
            main = getattr(module, "main", None)
            if main is None:
                return {
                    "success": False,
                    "message": "Skill script has no main() entry point: {}".format(script_path),
                }
            with _scene_edit(script_path):
                result = main(**params)
        except Exception as exc:  # noqa: BLE001
            return skill_exception(exc)
        if not isinstance(result, dict):
            return {
                "success": False,
                "message": "Skill script main() must return a dict: {}".format(script_path),
            }
        return result
    finally:
        sys.modules.pop(mod_name, None)
