"""Load a typed controller pose."""

from __future__ import annotations

from typing import Any, Dict

from meshy_dcc_3dsmax._pose_contract import load_pose
from meshy_dcc_3dsmax.api import get_runtime, with_max


@with_max
def main(pose_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate, load, and verify a typed controller pose."""
    return load_pose(get_runtime(), pose_data)
