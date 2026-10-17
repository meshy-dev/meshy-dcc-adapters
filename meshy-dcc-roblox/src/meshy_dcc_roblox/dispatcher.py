"""Run tool wrappers in the sidecar; their host calls go to the Studio plugin."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Callable

from meshy_dcc_core.skill import skill_success

from .bridge import call_host

current_action_name: ContextVar[str] = ContextVar("roblox_action", default="")


class RobloxBridgeDispatcher:
    """Run a tool's Python wrapper inline, remembering which tool it is."""

    def dispatch_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        action_name = kwargs.pop("action_name", "")
        for key in ("affinity", "context", "skill_name", "execution", "timeout_hint_secs"):
            kwargs.pop(key, None)
        token = current_action_name.set(action_name)
        try:
            return func(*args, **kwargs)
        finally:
            current_action_name.reset(token)


def dispatch(action_name: str, params: dict) -> Any:
    """Forward one declared tool to the plugin method of the same name."""
    action_name = (action_name or current_action_name.get()).rsplit("__", 1)[-1]
    if not action_name:
        raise ValueError("Roblox tool name is missing")
    result = call_host(action_name, params)
    if action_name == "session":
        # Studio has no plugin API for unsaved changes or for saving a place.
        result.setdefault("dirty", None)
    return skill_success(f"Roblox {action_name} completed.", **result)
