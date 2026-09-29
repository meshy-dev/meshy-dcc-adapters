"""Meshy DCC Unreal — manual startup helper script.

This script is an alternative to the full plugin.  Copy it to your project's
``Content/Python/`` directory to start the MCP server without installing the
plugin.

Usage
-----
Add to your project's Python startup scripts (Project Settings → Plugins →
Python → Additional Paths or Startup Scripts), or run manually from the
Unreal Editor Output Log:

    py meshy_dcc_unreal_startup.py

Or import from the Unreal Python console:

    import meshy_dcc_unreal_startup

Configuration (environment variables)
--------------------------------------
``MESHY_DCC_UNREAL_PORT``         Optional fixed MCP instance port.
``MESHY_DCC_UNREAL_SERVER_NAME``  MCP server name.  Default: ``"unreal-mcp"``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _bootstrap_log_dir() -> Path:
    plugin_root = _plugin_root()
    project_root = plugin_root.parent.parent if plugin_root.parent.name == "Plugins" else plugin_root.parent
    return project_root / ".meshy-dcc" / "bootstrap-errors"


def _adapter_version() -> str:
    try:
        descriptor = json.loads((_plugin_root() / "MeshyDccUnreal.uplugin").read_text(encoding="utf-8"))
        return str(descriptor.get("VersionName") or "unknown")
    except (OSError, ValueError):
        return "unknown"


def start() -> None:
    """Start the Meshy DCC Unreal server."""
    try:
        from meshy_dcc_core import capture_bootstrap_errors  # noqa: PLC0415

        with capture_bootstrap_errors(
            "unreal",
            adapter_version=_adapter_version(),
            min_core_version="0.2.0",
            phase="bootstrap",
            log_dir=str(_bootstrap_log_dir()),
            metadata={"runtime_mode": "manual-python"},
        ):
            import meshy_dcc_unreal  # noqa: PLC0415
            import unreal  # noqa: PLC0415

            server_name = os.environ.get("MESHY_DCC_UNREAL_SERVER_NAME", "unreal-mcp")
            handle = meshy_dcc_unreal.start_server(server_name=server_name)
            unreal.log(f"[meshy-dcc-unreal] MCP server running at {handle.mcp_url()}")
    except ImportError as exc:
        logger.error("[meshy-dcc-unreal] Import error: %s", exc)
        logger.error("Install the plugin: meshy-dcc install --dcc-type unreal --project <project root>")
    except Exception as exc:
        logger.error("[meshy-dcc-unreal] Failed to start: %s", exc)


def stop() -> None:
    """Stop the Meshy DCC Unreal server."""
    try:
        import meshy_dcc_unreal  # noqa: PLC0415

        meshy_dcc_unreal.stop_server()
    except Exception as exc:
        logger.warning("[meshy-dcc-unreal] Stop failed: %s", exc)


# Auto-start when script is executed or imported
start()
