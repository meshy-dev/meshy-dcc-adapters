"""SideFX Houdini adapter for Meshy DCC Core."""

from meshy_dcc_houdini.__version__ import __version__
from meshy_dcc_houdini._capability_manifest import (
    CapabilityRecord,
    HoudiniCapabilityManifestBuilder,
    build_manifest_payload,
    register_capability_mcp_tool,
)
from meshy_dcc_houdini._context_snapshot import (
    HoudiniContextSnapshotProvider,
    collect_gateway_metadata,
    make_snapshot_provider,
)
from meshy_dcc_houdini._env import (
    ENV_ENABLE_GATEWAY_FAILOVER,
    ENV_GATEWAY_PORT,
    ENV_METRICS,
    ENV_PORT,
    ENV_PROJECT_TOOLS,
    ENV_QT_UI_INSPECTOR,
    ENV_READINESS_TIMEOUT_SECS,
    ENV_RESOURCES,
    ENV_SEMANTIC_EMBEDDER,
    ENV_SEMANTIC_INDEX,
    resolve_enable_gateway_failover,
    resolve_minimal_mode_enabled,
)
from meshy_dcc_houdini._project_tools import (
    HoudiniSceneResolver,
    ProjectToolsIntegration,
)
from meshy_dcc_houdini._project_tools import (
    attach_to_server as attach_project_tools,
)
from meshy_dcc_houdini._qt_inspector import register_houdini_qt_ui_inspector
from meshy_dcc_houdini._readiness import ReadinessBinder, install_readiness
from meshy_dcc_houdini._resources import (
    HoudiniResourceBinder,
    install_resources,
)
from meshy_dcc_houdini._semantic_index import (
    HoudiniSemanticIndex,
    build_semantic_index,
)
from meshy_dcc_houdini._skill_loader import (
    MINIMAL_SKILLS,
    STAGE_SKILLS,
    STAGES,
    build_minimal_mode_config,
    build_minimal_mode_for_stages,
    skills_for_stage,
)
from meshy_dcc_houdini._version_probe import (
    get_houdini_version_string,
    get_houdini_version_tuple,
    is_houdini_available,
)
from meshy_dcc_houdini.api import (
    MissingParamError,
    get_param,
    houdini_error,
    houdini_from_exception,
    houdini_success,
    require_param,
    safe_parm_eval,
    safe_parm_node,
    with_houdini,
)
from meshy_dcc_houdini.api import (
    is_houdini_available as is_hou_available,
)
from meshy_dcc_houdini.dispatcher import (
    HoudiniStandaloneDispatcher,
    create_execution_stack,
)
from meshy_dcc_houdini.host import (
    HoudiniCallableDispatcher,
    HoudiniEventLoopTimerAdapter,
    HoudiniHost,
    HoudiniUiDispatcher,
    HoudiniUiPump,
)
from meshy_dcc_houdini.server import (
    DEFAULT_PORT,
    SERVER_NAME,
    HoudiniMcpServer,
    HoudiniServerOptions,
    get_server,
    serve_headless,
    start_server,
    stop_server,
)

__all__ = [
    "__version__",
    "DEFAULT_PORT",
    "ENV_ENABLE_GATEWAY_FAILOVER",
    "ENV_GATEWAY_PORT",
    "ENV_METRICS",
    "ENV_PORT",
    "ENV_PROJECT_TOOLS",
    "ENV_QT_UI_INSPECTOR",
    "ENV_READINESS_TIMEOUT_SECS",
    "ENV_RESOURCES",
    "ENV_SEMANTIC_EMBEDDER",
    "ENV_SEMANTIC_INDEX",
    "CapabilityRecord",
    "HoudiniCallableDispatcher",
    "HoudiniCapabilityManifestBuilder",
    "HoudiniContextSnapshotProvider",
    "HoudiniEventLoopTimerAdapter",
    "HoudiniHost",
    "HoudiniMcpServer",
    "HoudiniResourceBinder",
    "HoudiniSceneResolver",
    "HoudiniSemanticIndex",
    "HoudiniServerOptions",
    "HoudiniStandaloneDispatcher",
    "HoudiniUiDispatcher",
    "HoudiniUiPump",
    "MINIMAL_SKILLS",
    "MissingParamError",
    "ProjectToolsIntegration",
    "ReadinessBinder",
    "SERVER_NAME",
    "STAGES",
    "STAGE_SKILLS",
    "attach_project_tools",
    "build_manifest_payload",
    "build_minimal_mode_config",
    "build_minimal_mode_for_stages",
    "build_semantic_index",
    "collect_gateway_metadata",
    "create_execution_stack",
    "get_houdini_version_string",
    "get_houdini_version_tuple",
    "get_param",
    "get_server",
    "houdini_error",
    "houdini_from_exception",
    "houdini_success",
    "install_readiness",
    "install_resources",
    "is_houdini_available",
    "is_hou_available",
    "make_snapshot_provider",
    "register_capability_mcp_tool",
    "register_houdini_qt_ui_inspector",
    "require_param",
    "resolve_enable_gateway_failover",
    "resolve_minimal_mode_enabled",
    "safe_parm_eval",
    "safe_parm_node",
    "serve_headless",
    "skills_for_stage",
    "start_server",
    "stop_server",
    "with_houdini",
]
