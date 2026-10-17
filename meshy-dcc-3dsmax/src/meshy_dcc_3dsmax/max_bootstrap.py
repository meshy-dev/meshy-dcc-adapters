"""Bootstrap helpers for running meshy-dcc-3dsmax inside Autodesk 3ds Max."""

from __future__ import annotations

import atexit
import os
import site
import socket
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any, Optional

from meshy_dcc_3dsmax.__version__ import __version__
from meshy_dcc_3dsmax._constants import DEFAULT_GATEWAY_PORT
from meshy_dcc_3dsmax.sidecar.bridge import start_bridge, stop_bridge
from meshy_dcc_3dsmax.sidecar.qt_bridge import qt_bridge_port, start_qt_bridge, stop_qt_bridge

_sidecar_process: Optional[subprocess.Popen] = None
_sidecar_launch_contract: Optional[dict] = None
_cleanup_registered = False


def start_embedded_server(port: Optional[int] = None, **kwargs: Any) -> Any:
    """Start the embedded MCP HTTP server inside 3ds Max."""
    from meshy_dcc_3dsmax.server import start_server  # noqa: PLC0415

    resolved_port = int(port if port is not None else os.environ.get("MESHY_DCC_3DSMAX_PORT", "0"))
    kwargs.setdefault("gateway_port", _gateway_port(os.environ))
    kwargs.setdefault("registry_dir", os.environ.get("MESHY_DCC_REGISTRY_DIR") or None)
    return start_server(port=resolved_port, **kwargs)


def start_sidecar_bridge(
    bridge_port: Optional[int] = None,
    *,
    register_builtins: bool = True,
    include_bundled: bool = True,
) -> Any:
    """Start the discovery server, Qt host bridge, and external sidecar."""
    from meshy_dcc_3dsmax.dispatcher import create_dispatcher  # noqa: PLC0415

    _register_process_cleanup()
    _install_max_integration()
    dispatcher, pump = create_dispatcher()
    pump_installed = bool(pump is not None and pump.install())
    effective_dispatcher = dispatcher if pump is None or pump_installed else None
    discovery_server = start_embedded_server(
        gateway_port=0,
        register_builtins=register_builtins,
        include_bundled=include_bundled,
        dispatcher=effective_dispatcher,
    )
    qt_bridge = start_qt_bridge(bridge_port)
    discovery_mcp_url = "http://127.0.0.1:{}/mcp".format(discovery_server.port)
    process = start_sidecar_server(discovery_mcp_url=discovery_mcp_url)
    return {
        "discovery_server": discovery_server,
        "dispatcher": dispatcher,
        "pump": pump,
        "qt_bridge": qt_bridge,
        "sidecar_process": process,
    }


def start_sidecar_server(
    *,
    instance_id: Optional[str] = None,
    display_name: Optional[str] = None,
    discovery_mcp_url: Optional[str] = None,
) -> subprocess.Popen:
    """Start ``meshy-dcc-server.exe sidecar`` for gateway/admin registration."""
    global _sidecar_launch_contract, _sidecar_process

    if _sidecar_process is not None and _sidecar_process.poll() is None:
        return _sidecar_process

    binary = _server_binary_path()
    qt_port = qt_bridge_port()
    pid = os.getpid()
    env = dict(os.environ)
    try:
        from meshy_dcc_core.install_lifecycle import launch_sidecar  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("meshy_dcc_core.install_lifecycle.launch_sidecar is unavailable: {}".format(exc))

    gateway_remote_host, gateway_remote_port = _gateway_remote_options(env)
    result = launch_sidecar(
        dcc_type="3dsmax",
        host_rpc="qtserver://127.0.0.1:{}".format(qt_port),
        watch_pid=pid,
        server_bin=str(binary),
        instance_id=instance_id,
        display_name=display_name or _sidecar_display_name(),
        adapter_version=__version__,
        discovery_mcp_url=discovery_mcp_url,
        gateway_port=_gateway_port(env),
        gateway_name=_gateway_name(env),
        gateway_remote_host=gateway_remote_host,
        gateway_remote_port=gateway_remote_port,
        env=env,
        detached=True,
        liveness_check_secs=0.75,
        return_process=True,
    )
    if not result.get("success"):
        reason = result.get("reason") or "invalid_sidecar_launch"
        message = result.get("message") or "unknown launch failure"
        raise RuntimeError("failed to build sidecar launch command ({}): {}".format(reason, message))

    _sidecar_process = result.get("process")
    if _sidecar_process is None:
        raise RuntimeError("failed to launch sidecar: launch_sidecar did not return a process handle")
    _sidecar_launch_contract = {key: value for key, value in result.items() if key != "process"}
    print(
        "meshy-dcc-3dsmax sidecar server started pid={} ({})".format(
            _sidecar_process.pid,
            binary,
        )
    )
    gateway_port = int(result.get("gateway_port") or 0)
    if gateway_port > 0:
        print("meshy-dcc-3dsmax MCP gateway available at http://127.0.0.1:{}/mcp".format(gateway_port))
    else:
        print("meshy-dcc-3dsmax MCP gateway auto-launch disabled")
    return _sidecar_process


def stop_sidecar_bridge(timeout: float = 5.0) -> None:
    """Stop the external sidecar process and both localhost bridges."""
    global _sidecar_launch_contract, _sidecar_process

    _stop_embedded_server_if_loaded()
    _uninstall_embedded_pump()

    process = _sidecar_process
    _sidecar_process = None
    _sidecar_launch_contract = None
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)
        print("meshy-dcc-3dsmax sidecar server stopped pid={}".format(process.pid))

    stop_qt_bridge()
    stop_bridge()


def _stop_embedded_server_if_loaded() -> None:
    server_module = sys.modules.get("meshy_dcc_3dsmax.server")
    if server_module is None:
        return
    stop = getattr(server_module, "stop_server", None)
    if callable(stop):
        stop()


def _uninstall_embedded_pump() -> None:
    """Uninstall the embedded pump's .NET Timer and reset the singleton cache.

    Uses ``sys.modules`` lookup instead of a direct import so that calling
    ``stop_sidecar_bridge()`` alone does not pull in ``meshy_dcc_core``.
    """
    pump_mod = sys.modules.get("meshy_dcc_3dsmax.dispatcher.pump")
    if pump_mod is None:
        return
    _, pump = pump_mod.get_dispatcher()
    if pump is not None:
        pump.uninstall()
    pump_mod.reset_dispatcher()


def start_embedded_sidecar_bridge(
    bridge_port: Optional[int] = None,
    *,
    register_builtins: bool = True,
    include_bundled: bool = True,
) -> Any:
    """Start the agent-callable embedded MCP runtime with main-thread execution."""
    from meshy_dcc_3dsmax.dispatcher import create_dispatcher  # noqa: PLC0415
    from meshy_dcc_3dsmax.server import start_server  # noqa: PLC0415

    bridge = start_bridge(bridge_port)
    dispatcher, pump = create_dispatcher()
    pump_installed = False
    if pump is not None:
        pump_installed = pump.install()
    effective_dispatcher = dispatcher if pump is None or pump_installed else None
    server = start_server(
        port=int(os.environ.get("MESHY_DCC_3DSMAX_PORT", "0")),
        register_builtins=register_builtins,
        include_bundled=include_bundled,
        gateway_port=DEFAULT_GATEWAY_PORT,
        dispatcher=effective_dispatcher,
    )
    print("meshy-dcc-3dsmax MCP gateway available at http://127.0.0.1:{}/mcp".format(DEFAULT_GATEWAY_PORT))
    return {"bridge": bridge, "dispatcher": dispatcher, "pump": pump, "server": server}


def _server_binary_path() -> Path:
    override = os.environ.get("MESHY_DCC_SERVER_BIN")
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return path

    binary_name = "meshy-dcc-server.exe" if os.name == "nt" else "meshy-dcc-server"
    candidates = []
    candidates.extend(_bundled_server_binary_candidates(binary_name))
    server_root = os.environ.get("MESHY_DCC_SERVER_ROOT")
    if server_root:
        root = Path(server_root).expanduser()
        candidates.extend(
            [
                root / binary_name,
                root / "bin" / binary_name,
                root / "scripts" / binary_name,
                root / "Scripts" / binary_name,
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    current_scripts_binary = Path(sysconfig.get_path("scripts") or "") / binary_name
    if current_scripts_binary.is_file():
        return current_scripts_binary

    try:
        from meshy_dcc_server import binary_path  # noqa: PLC0415

        candidate = Path(binary_path())
        if candidate.is_file():
            return candidate
    except Exception:  # noqa: BLE001
        pass

    fallback_candidates = [Path(site.USER_BASE) / ("Scripts" if os.name == "nt" else "bin") / binary_name]
    try:
        user_site = Path(site.getusersitepackages())
        fallback_candidates.append(user_site.parent / ("Scripts" if os.name == "nt" else "bin") / binary_name)
    except Exception:  # noqa: BLE001
        pass
    for candidate in fallback_candidates:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "meshy-dcc-server binary not found. Set MESHY_DCC_SERVER_BIN to an explicit executable "
        "or install a payload that includes meshy-dcc-server."
    )


def _bundled_server_binary_candidates(binary_name: str) -> list[Path]:
    try:
        package_root = Path(__file__).resolve().parent.parent
    except OSError:
        return []
    return [
        package_root / "scripts" / binary_name,
        package_root / "Scripts" / binary_name,
        package_root / "bin" / binary_name,
        package_root / binary_name,
    ]


def _register_process_cleanup() -> None:
    global _cleanup_registered
    if _cleanup_registered:
        return
    atexit.register(stop_sidecar_bridge)
    _cleanup_registered = True


def _gateway_port(env: dict) -> int:
    raw = str(env.get("MESHY_DCC_GATEWAY_PORT", str(DEFAULT_GATEWAY_PORT))).strip()
    try:
        port = int(raw)
    except ValueError:
        return DEFAULT_GATEWAY_PORT
    if port < 0 or port > 65535:
        return DEFAULT_GATEWAY_PORT
    return port


def _gateway_remote_options(env: dict) -> tuple[str, int]:
    """The LAN gateway has no authentication: off (port 0) unless the operator sets a port."""
    host = str(env.get("MESHY_DCC_GATEWAY_REMOTE_HOST", "127.0.0.1")).strip() or "127.0.0.1"
    raw_port = str(env.get("MESHY_DCC_GATEWAY_REMOTE_PORT", "0")).strip()
    try:
        port = int(raw_port)
    except ValueError:
        port = 0
    if port < 0 or port > 65535:
        port = 0
    return host, port


def _gateway_name(env: dict) -> str:
    raw = env.get("MESHY_DCC_GATEWAY_NAME")
    if raw and str(raw).strip():
        return str(raw).strip()
    try:
        hostname = socket.gethostname().strip()
    except Exception:  # noqa: BLE001
        hostname = "localhost"
    return "meshy-dcc-gateway@{}".format(hostname or "localhost")


def _sidecar_display_name() -> str:
    return "3ds Max {} pid {}".format(_max_version_label(), os.getpid())


def _install_max_integration() -> None:
    try:
        from meshy_dcc_3dsmax.menu import install_menu, install_shutdown_callback  # noqa: PLC0415

        install_menu()
        install_shutdown_callback()
    except Exception as exc:  # noqa: BLE001
        print("meshy-dcc-3dsmax Max UI integration skipped: {}".format(exc))


def _max_version_label() -> str:
    try:
        import pymxs  # noqa: PLC0415

        runtime = pymxs.runtime
        version = runtime.maxVersion()
        product_version = _runtime_value(runtime, "productVersion")
        label = _year_label(product_version)
        if label:
            return label

        label = _version_sequence_year(version)
        if label:
            return label

        try:
            major = int(version[0])
        except Exception:  # noqa: BLE001
            return _sanitize_max_version_label(str(version))
        if major >= 10000:
            return _marketing_year_from_version_number(major)
        return _sanitize_max_version_label(str(major))
    except Exception:  # noqa: BLE001
        return "unknown"


def _runtime_value(runtime: Any, name: str) -> Any:
    try:
        value = getattr(runtime, name)
        return value() if callable(value) else value
    except Exception:  # noqa: BLE001
        return None


def _version_sequence_year(version: Any) -> Optional[str]:
    for index in (7, 6):
        try:
            label = _year_label(version[index])
        except Exception:  # noqa: BLE001
            continue
        if label:
            return label
    return _year_label(str(version))


def _marketing_year_from_version_number(version_num: int) -> str:
    major = version_num // 1000
    if major >= 15:
        return str(major + 1998)
    return str(major)


def _year_label(value: Any) -> Optional[str]:
    text = _sanitize_max_version_label(str(value)) if value not in (None, "") else ""
    match = None
    if text:
        import re  # noqa: PLC0415

        match = re.search(r"\b(20\d{2})\b", text)
    return match.group(1) if match else None


def _sanitize_max_version_label(value: str) -> str:
    cleaned = value
    for ch in ('"', "'", "\n", "\r", "\t"):
        cleaned = cleaned.replace(ch, " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip() or "unknown"


def main() -> Any:
    """Start the adapter in the mode ``MESHY_DCC_3DSMAX_BOOT_MODE`` names.

    The default, ``server``, runs the MCP server inside 3ds Max and registers it
    with the gateway, as the Blender adapter does; it needs nothing but this
    package and ``meshy_dcc_core``. ``sidecar`` starts an external
    ``meshy-dcc-server`` and needs that binary (``MESHY_DCC_SERVER_BIN``).
    """
    mode = os.environ.get("MESHY_DCC_3DSMAX_BOOT_MODE", "server").strip().lower()
    if mode in {"runtime", "sidecar"}:
        return start_sidecar_bridge()

    _register_process_cleanup()
    _install_max_integration()
    if mode in {"server", "embedded-server"}:
        return start_embedded_server()
    if mode in {"embedded", "embedded-sidecar", "bridge"}:
        return start_embedded_sidecar_bridge()
    raise ValueError("unsupported MESHY_DCC_3DSMAX_BOOT_MODE={!r}; expected runtime, sidecar, or server".format(mode))


def startup() -> Any:
    """Entry point of the startup script that ``host_install`` writes.

    Never raises: a failure is printed to the MAXScript Listener and recorded
    as a bootstrap error, and 3ds Max keeps starting.
    """
    try:
        from meshy_dcc_core import capture_bootstrap_errors  # noqa: PLC0415

        with capture_bootstrap_errors("3dsmax", adapter_version=__version__, min_core_version="0.2.0", phase="startup"):
            started = main()
            from meshy_dcc_3dsmax._safe_stop import attach_safe_stop  # noqa: PLC0415
            from meshy_dcc_3dsmax.server import get_server  # noqa: PLC0415

            attach_safe_stop(get_server())
            print("meshy-dcc-3dsmax {} started".format(__version__))
            return started
    except Exception as exc:  # noqa: BLE001 - a startup script must not break 3ds Max
        print("meshy-dcc-3dsmax did not start: {}: {}".format(type(exc).__name__, exc))
        return None


if __name__ == "__main__":
    main()
