"""Substance 3D Painter adapter for Meshy DCC."""

from meshy_dcc_substance3d_painter.__version__ import __version__
from meshy_dcc_substance3d_painter.server import (
    DEFAULT_PORT,
    SERVER_NAME,
    SubstancePainterMcpServer,
    get_server,
    start_server,
    stop_server,
)

STARTUP_PLUGIN_MODULE = "meshy_dcc_substance3d_painter_plugin"

__all__ = [
    "__version__",
    "DEFAULT_PORT",
    "SERVER_NAME",
    "SubstancePainterMcpServer",
    "get_server",
    "start_server",
    "stop_server",
    "STARTUP_PLUGIN_MODULE",
]
