"""Start Meshy DCC once the Houdini UI is ready (from the meshy_dcc_houdini package)."""

import os
import sys

_lib = os.path.join(os.environ.get("MESHY_DCC_HOUDINI_ROOT", ""), "lib")
if os.path.isdir(_lib) and _lib not in sys.path:
    sys.path.insert(0, _lib)

try:
    from meshy_dcc_houdini._autostart import autostart

    _server = autostart()
    if _server is not None:
        print("Meshy DCC for Houdini is listening on {}".format(_server.mcp_url))
except Exception as _exc:  # noqa: BLE001 - never break Houdini startup
    print("Meshy DCC autostart failed: {}".format(_exc))
