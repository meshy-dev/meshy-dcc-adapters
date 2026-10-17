"""Run meshy-dcc-maya from mayapy / maya.standalone.

Usage:
    mayapy examples/standalone/run_maya_mcp.py

Environment:
    MESHY_DCC_MAYA_PORT=<optional fixed instance port>
    MESHY_DCC_GATEWAY_PORT=0
    MESHY_DCC_MAYA_SKILL_PATHS=/path/to/custom-skills
"""

from __future__ import annotations

import os
import signal
import threading

import maya.standalone

from meshy_dcc_maya import start_server, stop_server
from meshy_dcc_maya.dispatcher import MayaStandaloneDispatcher

stop_event = threading.Event()


def _handle_stop(_signum, _frame) -> None:
    stop_event.set()
    stop_server()


def main() -> None:
    maya.standalone.initialize(name="python")

    gateway_raw = os.environ.get("MESHY_DCC_GATEWAY_PORT", "0")
    gateway_port = int(gateway_raw) if gateway_raw and gateway_raw != "0" else None

    dispatcher = MayaStandaloneDispatcher()
    handle = start_server(
        gateway_port=gateway_port,
        host_dispatcher=dispatcher,
    )

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    print("[meshy-dcc-maya] standalone MCP:", handle.mcp_url())
    print("[meshy-dcc-maya] press Ctrl+C to stop")
    stop_event.wait()


if __name__ == "__main__":
    main()
