"""Auto-start the MCP server when Houdini launches.

Install (pick one):

* Windows user scripts:
  ``%USERPROFILE%\\Documents\\houdini20.5\\scripts\\123.py``
* Or set ``HOUDINI_PATH`` / ``HS/site`` to a folder containing this file as ``123.py``

Set ``MESHY_DCC_HOUDINI_AUTOSTART=0`` to disable.
"""

from __future__ import annotations

import os


def _autostart_enabled() -> bool:
    raw = os.environ.get("MESHY_DCC_HOUDINI_AUTOSTART", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


if _autostart_enabled():
    try:
        import meshy_dcc_houdini

        server = meshy_dcc_houdini.start_server()
        print(f"[meshy-dcc-houdini] auto-started: {server.mcp_url}")
    except Exception as exc:  # noqa: BLE001
        print(f"[meshy-dcc-houdini] autostart failed: {exc}")
