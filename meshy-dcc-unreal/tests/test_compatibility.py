from pathlib import Path

import pytest

from meshy_dcc_unreal.compatibility import parse_unreal_version, resolve_unreal_runtime, unreal_compatibility


@pytest.mark.parametrize(
    ("version", "expected"),
    [("4.18.3", (4, 18)), ("5.8.0-55116800+++UE5+Release-5.8", (5, 8))],
)
def test_parse_unreal_version(version, expected):
    assert parse_unreal_version(version) == expected


def test_unreal_engine_4_is_not_supported():
    compatibility = unreal_compatibility("4.27", has_embedded_python=False)
    assert compatibility["supported"] is False
    assert compatibility["integration_tier"] == "unsupported"
    assert compatibility["minimum_version"] == "5.0"
    with pytest.raises(ValueError, match="5.0 or newer"):
        resolve_unreal_runtime("4.27.2", "auto")


def test_ue5_auto_runtime_is_embedded_python():
    assert resolve_unreal_runtime("5.0.3", "auto") == "python"
    assert unreal_compatibility("5.7", has_embedded_python=True)["integration_tier"] == "meshy-dcc-python"


def test_unreal_startup_resolves_runtime_before_importing_the_package():
    startup = (Path(__file__).parents[1] / "unreal" / "plugin" / "Content" / "Python" / "init_unreal.py").read_text(
        encoding="utf-8"
    )

    assert "_resolve_bootstrap_runtime()" in startup
    assert "SystemLibrary.get_engine_version()" in startup
    assert 'if _runtime_mode != "sidecar":' in startup


def test_ue58_can_compose_dcc_and_epic_mcp():
    compatibility = unreal_compatibility("5.8", has_embedded_python=True, has_official_mcp=True)
    assert compatibility["integration_tier"] == "meshy-dcc-plus-epic"
    assert compatibility["official_mcp_bridge"] is True
