"""Create a box primitive in 3ds Max."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any

# Import local modules
from meshy_dcc_3dsmax._scene_utils import set_node_position
from meshy_dcc_3dsmax.api import get_runtime, with_max


@with_max
def main(
    width: float = 100.0,
    height: float = 100.0,
    depth: float = 100.0,
    name: str = None,
    position: Any = None,
) -> dict:
    """Create a box with the given parameters.

    Returns
    -------
    dict
        The action response.
    """
    rt = get_runtime()
    # A 3ds Max Box has no `depth`: its third size is `length`, and pymxs
    # ignores an unknown keyword, which left every box 25 units long.
    box_obj = rt.Box(width=width, length=depth, height=height)

    if name:
        box_obj.name = name
    applied_position = set_node_position(rt, box_obj, position)

    return {
        "success": True,
        "message": f"Created box: {box_obj.name}",
        "data": {
            "node_name": str(box_obj.name),
            "object_id": int(box_obj.handle) if hasattr(box_obj, "handle") else None,
            "width": float(box_obj.width),
            "height": float(box_obj.height),
            "depth": float(box_obj.length),
            "position": applied_position,
        },
    }
