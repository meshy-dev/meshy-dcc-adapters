"""Read 3ds Max scene color-management settings."""

from __future__ import annotations

from typing import Any, Dict

from meshy_dcc_3dsmax._lookdev_utils import get_color_management
from meshy_dcc_3dsmax.api import get_runtime, with_max


@with_max
def main() -> Dict[str, Any]:
    import pymxs

    return get_color_management(get_runtime(), byref=getattr(pymxs, "byref", None))
