"""Unreal version and optional-backend capability negotiation."""

from __future__ import annotations

import re
from typing import Dict, Tuple

MINIMUM_UNREAL_VERSION = (5, 0)
OFFICIAL_MCP_VERSION = (5, 8)


def parse_unreal_version(value: str) -> Tuple[int, int]:
    """Return an Unreal major/minor pair from an engine version string."""
    match = re.match(r"\s*(\d+)\.(\d+)", value)
    if not match:
        raise ValueError("Invalid Unreal Engine version: {!r}".format(value))
    return int(match.group(1)), int(match.group(2))


def resolve_unreal_runtime(engine_version: str, runtime_mode: str = "auto") -> str:
    """Resolve ``auto`` to the embedded Python runtime; Unreal Engine 4 is not supported."""
    mode = (runtime_mode or "auto").strip().lower()
    if mode != "auto":
        return mode
    if parse_unreal_version(engine_version) < MINIMUM_UNREAL_VERSION:
        raise ValueError("Unreal Engine {} is not supported; 5.0 or newer is required".format(engine_version))
    return "python"


def unreal_compatibility(
    engine_version: str,
    has_embedded_python: bool,
    has_official_mcp: bool = False,
) -> Dict[str, object]:
    """Describe supported integration layers without calling unavailable APIs."""
    version = parse_unreal_version(engine_version)
    supported = version >= MINIMUM_UNREAL_VERSION
    official_bridge = supported and version >= OFFICIAL_MCP_VERSION and has_official_mcp
    if official_bridge and has_embedded_python:
        integration_tier = "meshy-dcc-plus-epic"
    elif has_embedded_python and supported:
        integration_tier = "meshy-dcc-python"
    elif supported:
        integration_tier = "native-baseline"
    else:
        integration_tier = "unsupported"

    limitations = []
    if supported and not has_embedded_python:
        limitations.append(
            "Python skills require an external sidecar or an engine installation with PythonScriptPlugin"
        )
    if version < OFFICIAL_MCP_VERSION:
        limitations.append("Epic Unreal MCP and Toolset Registry bridging require Unreal Engine 5.8+")
    elif not has_official_mcp:
        limitations.append("Epic Unreal MCP is optional and is not currently available")

    return {
        "engine_version": engine_version,
        "minimum_version": "5.0",
        "supported": supported,
        "integration_tier": integration_tier,
        "native_baseline": supported,
        "embedded_python": supported and has_embedded_python,
        "official_mcp_bridge": official_bridge,
        "limitations": limitations,
    }
