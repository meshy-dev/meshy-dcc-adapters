"""Tests for the meshy-dcc-core dependency range."""

from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).parent.parent


def _load_assemble_zip_module():
    path = ROOT / "packaging" / "assemble_zip.py"
    spec = importlib.util.spec_from_file_location("assemble_zip_for_tests", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_core_dependency_range_is_pinned_to_the_02x_series():
    """A future Core minor must fail at install time, not inside the matrix."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"meshy-dcc-core>=0.2.0,<0.3.0"' in pyproject


def _core_constraint():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'"meshy-dcc-core>=(?P<min>[^,]+),<(?P<max>[^"]+)"', pyproject)

    assert match is not None
    return match.group("min"), match.group("max")


def test_packaging_core_floor_matches_pyproject():
    min_version, _ = _core_constraint()

    assert _load_assemble_zip_module().MIN_CORE_VERSION == min_version


def test_packaging_core_ceiling_matches_pyproject():
    """The addon ZIP must never bundle a Core the dependency spec rejects."""
    _, max_version = _core_constraint()

    assert _load_assemble_zip_module().MAX_CORE_VERSION == max_version


def test_packaging_resolver_ignores_releases_above_the_ceiling(monkeypatch):
    """The resolver must filter on the ceiling, not merely declare it.

    Asserting that ``MAX_CORE_VERSION`` equals the pyproject bound only pins a
    constant. Filtering on ``< 1.0.0`` while leaving the constant untouched
    keeps that test green and ships an addon ZIP bundling a Core the adapter's
    own dependency spec refuses to install next to.
    """
    module = _load_assemble_zip_module()
    releases = ["0.2.1", "0.2.3", "0.3.0", "0.3.2", "1.0.0"]
    monkeypatch.setattr(module, "_fetch_json", lambda url: {"releases": {name: [] for name in releases}})

    assert module.resolve_core_version() == "0.2.3"


def test_preloaded_core_below_floor_is_rejected():
    from meshy_dcc_blender._core_compat import require_compatible_core

    with pytest.raises(RuntimeError, match="preloaded meshy-dcc-core 0.1.94"):
        require_compatible_core("0.1.94", module_path="/host/site-packages/meshy_dcc_core")


def test_preloaded_core_at_floor_is_accepted():
    from meshy_dcc_blender._core_compat import require_compatible_core

    require_compatible_core("0.2.0", module_path="/extension/site-packages/meshy_dcc_core")
