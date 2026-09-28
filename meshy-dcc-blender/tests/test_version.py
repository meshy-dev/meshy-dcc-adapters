"""Basic version and import tests that don't require bpy."""

from __future__ import annotations


def test_version_string():
    """Version should be a valid semver-like string."""
    from meshy_dcc_blender.__version__ import __version__

    parts = __version__.split(".")
    assert len(parts) == 3
    for p in parts:
        assert p.isdigit(), f"Version part '{p}' is not numeric"


def test_version_accessible_from_package():
    """__version__ should be importable from the top-level package."""
    import meshy_dcc_blender

    assert hasattr(meshy_dcc_blender, "__version__")
    assert isinstance(meshy_dcc_blender.__version__, str)
