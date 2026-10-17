"""Start the adapter when an interactive Houdini session is ready.

The package's ``pythonX.Ylibs/uiready.py`` calls :func:`autostart`. Houdini
runs every ``uiready.py`` on its path, in interactive sessions only, so the
hook does not shadow a user's own startup scripts the way ``123.py`` and
``456.py`` (first match wins) would.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

_OFF = {"0", "false", "no", "off"}


def autostart(environ: Mapping[str, str] = os.environ) -> Optional[Any]:
    """Start the server unless disabled, in a background job, or without a UI."""
    if environ.get("MESHY_DCC_BACKGROUND_RENDER") == "1" or environ.get("MESHY_DCC_BACKGROUND_COOK") == "1":
        return None
    if environ.get("MESHY_DCC_HOUDINI_AUTOSTART", "1").strip().lower() in _OFF:
        return None
    import hou  # noqa: PLC0415 - only importable inside Houdini

    if not hou.isUIAvailable():
        return None

    from meshy_dcc_core import capture_bootstrap_errors  # noqa: PLC0415

    from meshy_dcc_houdini import __version__, start_server  # noqa: PLC0415
    from meshy_dcc_houdini._installer import MIN_CORE_VERSION  # noqa: PLC0415

    with capture_bootstrap_errors(
        "houdini", adapter_version=__version__, min_core_version=MIN_CORE_VERSION, phase="uiready"
    ):
        gateway = environ.get("MESHY_DCC_GATEWAY_PORT", "")
        return start_server(
            gateway_port=int(gateway) if gateway.isdigit() else None,
            registry_dir=environ.get("MESHY_DCC_REGISTRY_DIR") or None,
            wait_ready=False,
        )
