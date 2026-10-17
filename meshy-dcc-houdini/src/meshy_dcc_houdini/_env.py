"""Environment variable helpers for meshy-dcc-houdini."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CORE_LOG_LEVEL_ENV = "MESHY_DCC_LOG_LEVEL"
LEGACY_CORE_LOG_LEVEL_ENV = "MCP_LOG_LEVEL"
DEFAULT_CORE_LOG_LEVEL = "WARN"


def configure_core_logging() -> None:
    """Keep meshy-dcc-core's default HTTP tracing out of Houdini's console."""
    log_level = (
        os.environ.get(CORE_LOG_LEVEL_ENV) or os.environ.get(LEGACY_CORE_LOG_LEVEL_ENV) or DEFAULT_CORE_LOG_LEVEL
    )
    os.environ.setdefault(CORE_LOG_LEVEL_ENV, log_level)
    os.environ.setdefault(LEGACY_CORE_LOG_LEVEL_ENV, log_level)


configure_core_logging()

ENV_METRICS = "MESHY_DCC_HOUDINI_METRICS"
ENV_JOB_STORAGE = "MESHY_DCC_HOUDINI_JOB_STORAGE_PATH"
ENV_ENABLE_WORKFLOWS = "MESHY_DCC_HOUDINI_ENABLE_WORKFLOWS"
ENV_ENABLE_GATEWAY_FAILOVER = "MESHY_DCC_HOUDINI_ENABLE_GATEWAY_FAILOVER"
ENV_READINESS_TIMEOUT_SECS = "MESHY_DCC_HOUDINI_READINESS_TIMEOUT_SECS"
ENV_PORT = "MESHY_DCC_HOUDINI_PORT"
ENV_GATEWAY_PORT = "MESHY_DCC_GATEWAY_PORT"

# Optional core-integration opt-out / opt-in switches (parity with Maya).
ENV_RESOURCES = "MESHY_DCC_HOUDINI_RESOURCES"
ENV_PROJECT_TOOLS = "MESHY_DCC_HOUDINI_PROJECT_TOOLS"
ENV_QT_UI_INSPECTOR = "MESHY_DCC_HOUDINI_QT_UI_INSPECTOR"
ENV_SEMANTIC_INDEX = "MESHY_DCC_HOUDINI_SEMANTIC_INDEX"
ENV_SEMANTIC_EMBEDDER = "MESHY_DCC_HOUDINI_SEMANTIC_EMBEDDER"

DEFAULT_JOB_DB_FILENAME = "jobs.db"

_TRUTHY = ("1", "true", "yes", "on")


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def get_extra_skill_paths() -> list[str]:
    """Read MESHY_DCC_HOUDINI_SKILL_PATHS and MESHY_DCC_SKILL_PATHS."""
    sep = ";" if os.sep == "\\" else ":"
    paths: list[str] = []

    for env_var in ("MESHY_DCC_HOUDINI_SKILL_PATHS", "MESHY_DCC_SKILL_PATHS"):
        raw = os.environ.get(env_var, "")
        if raw:
            for part in raw.split(sep):
                part = part.strip()
                if part:
                    paths.append(part)

    return paths


def resolve_enable_gateway_failover(value: Optional[bool]) -> bool:
    """Resolve enable_gateway_failover with env var fallback."""
    if value is not None:
        return value
    raw = os.environ.get(ENV_ENABLE_GATEWAY_FAILOVER, "").strip()
    if raw:
        return _env_truthy(ENV_ENABLE_GATEWAY_FAILOVER)
    return True


def resolve_metrics_enabled(value: Optional[bool]) -> bool:
    """Resolve metrics_enabled with env var fallback."""
    if value is not None:
        return bool(value)
    return _env_truthy(ENV_METRICS)


def resolve_job_storage(value: Optional[str]) -> Optional[str]:
    """Resolve job_storage_path with env var fallback."""
    if value is not None:
        if not str(value).strip():
            return ""
        return value

    env_val = os.environ.get(ENV_JOB_STORAGE)
    if env_val is not None:
        return env_val

    try:
        from meshy_dcc_core import get_data_dir  # noqa: PLC0415

        data_dir = Path(get_data_dir()) / "meshy-dcc-houdini"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir / DEFAULT_JOB_DB_FILENAME)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not resolve default job storage path: %s", exc)
        return None


def resolve_enable_workflows(value: Optional[bool]) -> bool:
    """Resolve enable_workflows with env var fallback."""
    if value is not None:
        return value
    return _env_truthy(ENV_ENABLE_WORKFLOWS)


def resolve_minimal_mode_enabled() -> bool:
    """Return True when progressive minimal mode should be used at startup."""
    raw = os.environ.get("MESHY_DCC_MINIMAL", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _resolve_default_on(env_name: str, flag: Optional[bool]) -> bool:
    """Resolve an opt-out switch: explicit ``flag`` > env (``"0"`` disables) > True."""
    if flag is not None:
        return bool(flag)
    raw = os.environ.get(env_name)
    if raw is None:
        return True
    return raw.strip() != "0"


def resolve_resources_enabled(flag: Optional[bool] = None) -> bool:
    """Resolve whether MCP resource publishing should run (default enabled)."""
    return _resolve_default_on(ENV_RESOURCES, flag)


def resolve_project_tools_enabled(flag: Optional[bool] = None) -> bool:
    """Resolve whether project-state tools should be wired (default enabled)."""
    return _resolve_default_on(ENV_PROJECT_TOOLS, flag)


def resolve_qt_ui_inspector_enabled(env: Optional[dict] = None) -> bool:
    """Return ``True`` unless ``MESHY_DCC_HOUDINI_QT_UI_INSPECTOR`` is falsey (default on)."""
    environ = env if env is not None else os.environ
    return str(environ.get(ENV_QT_UI_INSPECTOR, "1")).strip().lower() in _TRUTHY


def resolve_semantic_index_enabled(env: Optional[dict] = None) -> bool:
    """Return ``True`` when ``MESHY_DCC_HOUDINI_SEMANTIC_INDEX`` is truthy (default off)."""
    environ = env if env is not None else os.environ
    return str(environ.get(ENV_SEMANTIC_INDEX, "")).strip().lower() in _TRUTHY


def resolve_semantic_embedder_kind(env: Optional[dict] = None) -> str:
    """Return the embedder kind: ``"hashed"`` (default) or ``"onnx"``."""
    environ = env if env is not None else os.environ
    kind = str(environ.get(ENV_SEMANTIC_EMBEDDER, "hashed")).strip().lower()
    return "onnx" if kind == "onnx" else "hashed"
