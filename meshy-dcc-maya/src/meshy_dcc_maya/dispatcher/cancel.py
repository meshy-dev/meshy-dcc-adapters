"""Cooperative cancellation checkpoint for Maya skill scripts.

Delegates to :func:`meshy_dcc_core.cancellation.check_dcc_cancelled`, which
honours both the MCP cancel token and the per-job handle published by
:class:`~meshy_dcc_core.HostUiDispatcherBase` during job execution.
"""

from __future__ import annotations

from meshy_dcc_core.cancellation import CancelledError, check_dcc_cancelled

__all__ = ["CancelledError", "check_maya_cancelled"]


def check_maya_cancelled() -> None:
    """Raise :class:`~meshy_dcc_core.cancellation.CancelledError` on cancellation."""
    check_dcc_cancelled()
