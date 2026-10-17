"""Painter startup entry point for the Meshy DCC adapter."""

from meshy_dcc_core import capture_bootstrap_errors

from meshy_dcc_substance3d_painter.__version__ import __version__

_CAPTURE = {
    "dcc_name": "substance3d_painter",
    "adapter_version": __version__,
    "min_core_version": "0.2.0",
}

with capture_bootstrap_errors(phase="import", **_CAPTURE):
    from meshy_dcc_substance3d_painter.plugin import close_plugin as _close_plugin
    from meshy_dcc_substance3d_painter.plugin import start_plugin as _start_plugin


def start_plugin():
    with capture_bootstrap_errors(phase="startup", **_CAPTURE):
        return _start_plugin()


def close_plugin():
    with capture_bootstrap_errors(phase="shutdown", **_CAPTURE):
        return _close_plugin()


__all__ = ["close_plugin", "start_plugin"]
