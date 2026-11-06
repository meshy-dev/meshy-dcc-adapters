"""Detect ZBrush Python SDK availability and version."""

from __future__ import annotations

import os
from typing import Optional, Tuple

# ZBrush Python SDK, ``zbrush_info``:
#   0 -> the ZBrush version number (float, e.g. 2026.0)
#   1 -> the edition type (float): 0 = Demo, 1 = Beta, 2 = Full
# Index 1 is the edition, not a minor version. Reading it as one reported a Full
# edition ZBrush 2027.0.1 as "2027.2".
ZBRUSH_INFO_VERSION = 0
ZBRUSH_INFO_EDITION = 1
ZBRUSH_EDITIONS = {0: "Demo", 1: "Beta", 2: "Full"}


def is_zbrush_available() -> bool:
    """Return True when ``zbrush.commands`` can be imported (inside ZBrush)."""
    try:
        import zbrush.commands  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def format_sdk_version(value: float) -> str:
    """Format ``zbrush_info(0)`` with its precision and at least two components."""
    text = f"{float(value):.3f}".rstrip("0").rstrip(".")
    return f"{text}.0" if "." not in text else text


def read_sdk_version(zbc) -> Tuple[str, int]:
    """Return ``(version, edition)``; the edition is never part of the version.

    An unreadable edition is ``-1``.
    """
    version = format_sdk_version(zbc.zbrush_info(ZBRUSH_INFO_VERSION))
    try:
        edition = int(zbc.zbrush_info(ZBRUSH_INFO_EDITION))
    except (TypeError, ValueError):
        edition = -1
    return version, edition


def get_zbrush_version_string() -> str:
    """Return a human-readable ZBrush version or ``unknown``.

    Inside ZBrush it comes from the SDK; the sidecar gets it from the bridge
    that started it (``MESHY_DCC_ZBRUSH_VERSION``).
    """
    try:
        import zbrush.commands as zbc  # noqa: PLC0415

        return read_sdk_version(zbc)[0]
    except Exception:
        return os.environ.get("MESHY_DCC_ZBRUSH_VERSION") or "unknown"


def get_zbrush_edition() -> int:
    """Return the edition type (0 Demo, 1 Beta, 2 Full) or ``-1`` outside ZBrush."""
    try:
        import zbrush.commands as zbc  # noqa: PLC0415

        return read_sdk_version(zbc)[1]
    except Exception:
        return -1


def get_zbrush_version_tuple() -> Tuple[int, int]:
    """Return ``(major, minor)`` from the SDK version number, or ``(0, 0)``."""
    try:
        import zbrush.commands as zbc  # noqa: PLC0415

        major, _, minor = read_sdk_version(zbc)[0].partition(".")
        return int(major), int(minor)
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
