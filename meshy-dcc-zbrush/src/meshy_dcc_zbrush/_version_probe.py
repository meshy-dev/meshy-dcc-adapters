"""Detect ZBrush Python SDK availability and version."""

from __future__ import annotations

import os
from typing import Optional, Tuple


def is_zbrush_available() -> bool:
    """Return True when ``zbrush.commands`` can be imported (inside ZBrush)."""
    try:
        import zbrush.commands  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def get_zbrush_version_string() -> str:
    """Return a human-readable ZBrush version or ``unknown``.

    Inside ZBrush it comes from the SDK; the sidecar gets it from the bridge
    that started it (``MESHY_DCC_ZBRUSH_VERSION``).
    """
    try:
        import zbrush.commands as zbc  # noqa: PLC0415

        major = int(zbc.zbrush_info(0))
        minor = int(zbc.zbrush_info(1))
        return f"{major}.{minor}"
    except Exception:
        return os.environ.get("MESHY_DCC_ZBRUSH_VERSION") or "unknown"


def get_zbrush_version_tuple() -> Tuple[int, int]:
    """Return ``(major, minor)`` from ``zbrush_info`` or ``(0, 0)``."""
    try:
        import zbrush.commands as zbc  # noqa: PLC0415

        return int(zbc.zbrush_info(0)), int(zbc.zbrush_info(1))
    except Exception:
        return 0, 0


def get_active_tool_path() -> Optional[str]:
    """Return the active tool path when running inside ZBrush."""
    try:
        import zbrush.commands as zbc  # noqa: PLC0415

        path = zbc.get_active_tool_path()
        return str(path) if path else None
    except Exception:
        return None
