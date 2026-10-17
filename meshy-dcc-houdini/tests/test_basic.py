"""Basic tests for meshy-dcc-houdini."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_import() -> None:
    """Test that meshy_dcc_houdini can be imported."""
    import meshy_dcc_houdini

    assert hasattr(meshy_dcc_houdini, "__version__")
    assert hasattr(meshy_dcc_houdini, "HoudiniMcpServer")


def test_version() -> None:
    """Test version is a string."""
    from meshy_dcc_houdini import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_server_options() -> None:
    """Test HoudiniServerOptions dataclass."""
    from meshy_dcc_houdini.server import HoudiniServerOptions

    opts = HoudiniServerOptions()
    assert opts.port is None
    assert opts.server_name == "meshy-dcc-houdini"
    assert opts.gateway_port is None


def test_server_options_to_core() -> None:
    """Test HoudiniServerOptions.to_core_options()."""
    from meshy_dcc_houdini.server import HoudiniServerOptions

    opts = HoudiniServerOptions(port=9000, dcc_version="20.5")
    core_opts = opts.to_core_options()

    assert core_opts is not None
    assert core_opts.port == 9000


def test_server_options_preserve_explicit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit dynamic-port request must not be replaced by the environment."""
    monkeypatch.setenv("MESHY_DCC_HOUDINI_PORT", "18765")

    from meshy_dcc_houdini.server import HoudiniServerOptions

    assert HoudiniServerOptions(port=0).to_core_options().port == 0


def test_server_reads_extra_skill_paths_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from meshy_dcc_houdini.server import HoudiniMcpServer

    skill_path = tmp_path / "lookdev-skill"
    skill_path.mkdir()
    monkeypatch.delenv("MESHY_DCC_HOUDINI_SKILL_PATHS", raising=False)
    monkeypatch.setenv("MESHY_DCC_SKILL_PATHS", str(skill_path))

    server = HoudiniMcpServer(port=0, gateway_port=0, enable_gateway_failover=False, job_storage_path="")
    try:
        assert server._extra_skill_paths == [str(skill_path)]
    finally:
        server.stop()


def test_file_registry_registration_survives_disabled_failover(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disabling failover must not disable FileRegistry self-registration."""
    monkeypatch.setenv("MESHY_DCC_GATEWAY_PORT", "19876")

    from meshy_dcc_houdini.server import HoudiniMcpServer

    server = HoudiniMcpServer(port=0, enable_gateway_failover=False, job_storage_path="")
    try:
        assert server._enable_gateway_failover is False
        assert server._config.gateway_port == 19876
    finally:
        server.stop()


def test_explicit_zero_gateway_port_disables_registration() -> None:
    """gateway_port=0 remains the explicit opt-out for FileRegistry registration."""
    from meshy_dcc_houdini.server import HoudiniMcpServer

    server = HoudiniMcpServer(port=0, gateway_port=0, enable_gateway_failover=False, job_storage_path="")
    try:
        assert server._config.gateway_port == 0
    finally:
        server.stop()


@pytest.mark.skip(reason="Requires Houdini environment")
def test_server_creation() -> None:
    """Test HoudiniMcpServer creation (requires Houdini)."""
    from meshy_dcc_houdini.server import HoudiniMcpServer

    server = HoudiniMcpServer(port=18765)
    assert server is not None
    server.shutdown()
