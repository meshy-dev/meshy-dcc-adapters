"""Meshy DCC server for Material Maker: one instance per material project folder."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Optional

from meshy_dcc_core import DccServerOptions, MinimalModeConfig
from meshy_dcc_core.server_base import DccServerBase

from .__version__ import __version__
from .bridge import MaterialMakerCli
from .project_install import read_project_config

logger = logging.getLogger(__name__)
SERVER_NAME = "meshy-dcc-material-maker"
DCC_TYPE = "material-maker"
START_OPERATION_ENV = "MESHY_DCC_START_OPERATION_ID"
START_PROJECT_ENV = "MESHY_DCC_START_PROJECT"
_BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent / "skills"
_server: Optional["MaterialMakerMcpServer"] = None
_stopped = threading.Event()
STOP_DELAY_SECS = 0.5


def configure_project(project: Optional[str]) -> Optional[Path]:
    """Bind the tools to a project folder and its recorded Material Maker.

    Tool scripts run as child processes, so the binding travels in the
    environment: the project, and the executable the installer recorded
    unless the operator set one.
    """
    value = project or os.environ.get(START_PROJECT_ENV)
    if not value:
        return None
    root = Path(value).expanduser().resolve()
    os.environ["MESHY_DCC_MATERIAL_MAKER_PROJECT"] = str(root)
    config = read_project_config(root)
    if config.get("executable") and not os.environ.get("MESHY_DCC_MATERIAL_MAKER_EXECUTABLE"):
        os.environ["MESHY_DCC_MATERIAL_MAKER_EXECUTABLE"] = str(config["executable"])
    return root


class MaterialMakerMcpServer(DccServerBase):
    """Standalone adapter: edits .ptex graphs and exports through Material Maker's CLI."""

    def __init__(
        self,
        port: Optional[int] = None,
        extra_skill_paths: Optional[list[str]] = None,
        gateway_port: Optional[int] = None,
        registry_dir: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        os.environ.setdefault("MESHY_DCC_PYTHON_EXECUTABLE", sys.executable)
        self._extra_skill_paths = list(extra_skill_paths or [])
        cli = MaterialMakerCli.from_env()
        kwargs.setdefault("scene", str(cli.project_root))
        options = DccServerOptions.from_env(
            DCC_TYPE,
            _BUILTIN_SKILLS_DIR,
            port=port,
            server_name=SERVER_NAME,
            server_version=__version__,
            adapter_version=__version__,
            dcc_version=cli.version() or "unknown",
            instance_type="standalone",
            standalone_main_thread=False,
            gateway_port=gateway_port,
            registry_dir=registry_dir,
            **kwargs,
        )
        super().__init__(options=options)

    def _version_string(self) -> str:
        return __version__

    @property
    def port(self) -> int:
        if self._handle is not None:
            return int(self._handle.port)
        return int(self._options.port)

    @property
    def mcp_url(self) -> str:
        return "http://127.0.0.1:{}/mcp".format(self.port)

    def register_builtin_actions(
        self,
        extra_skill_paths: Optional[list[str]] = None,
        include_bundled: bool = True,
        minimal_mode: Optional[MinimalModeConfig] = None,
    ) -> None:
        paths = list(self._extra_skill_paths)
        if extra_skill_paths:
            paths.extend(extra_skill_paths)
        super().register_builtin_actions(
            extra_skill_paths=paths,
            include_bundled=include_bundled,
            minimal_mode=minimal_mode,
        )


def handle_stop_request(body: dict, instance_id: Any) -> tuple[int, dict]:
    """Every edit is written to its .ptex at once, so nothing is ever unsaved."""
    if not instance_id or body.get("instance_id") != instance_id:
        return 409, {"stopping": False, "reason": "instance_mismatch"}
    # Exit after this reply has gone out; exiting at once cut it off mid-body.
    threading.Timer(STOP_DELAY_SECS, _stopped.set).start()
    return 202, {"stopping": True}


def attach_safe_stop(server: MaterialMakerMcpServer) -> None:
    """Advertise ``safe_stop_url`` in the registry row of a start-instance launch."""
    if not os.environ.get(START_OPERATION_ENV):
        return
    handle = getattr(server, "_handle", None)
    if handle is None:
        return
    from meshy_dcc_core.host.safe_stop import serve_safe_stop

    url = serve_safe_stop(lambda body: handle_stop_request(body, server.instance_id))
    handle.update_gateway_metadata({"safe_stop_url": url})


def start_server(
    port: Optional[int] = None,
    extra_skill_paths: Optional[list[str]] = None,
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    **kwargs: Any,
) -> MaterialMakerMcpServer:
    global _server
    if _server is None:
        server = MaterialMakerMcpServer(
            port=port,
            extra_skill_paths=extra_skill_paths,
            gateway_port=gateway_port,
            registry_dir=registry_dir,
            **kwargs,
        )
        server.register_builtin_actions()
        server.start()
        attach_safe_stop(server)
        _server = server
        logger.info("Material Maker MCP server started")
    return _server


def stop_server() -> None:
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def serve(project: Optional[str] = None) -> None:
    """Run until interrupted or asked to stop."""
    configure_project(project)
    signal.signal(signal.SIGINT, lambda *_: _stopped.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: _stopped.set())
    start_server()
    try:
        _stopped.wait()
    finally:
        stop_server()


def main(argv: Optional[list[str]] = None) -> None:
    from .cli import main as cli_main

    code = cli_main(argv)
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
