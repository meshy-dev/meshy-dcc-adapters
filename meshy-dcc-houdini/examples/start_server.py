"""Example: start meshy-dcc-houdini inside Houdini.

Run in Houdini's Python Source Editor. For headless Hython use:

    hython examples/houdini_bootstrap.py
"""

from __future__ import annotations

import meshy_dcc_houdini

print("Starting meshy-dcc-houdini server...")
server = meshy_dcc_houdini.start_server()
print(f"MCP endpoint: {server.mcp_url}")
print(f"Loaded skills: {server.loaded_skill_count()}")
