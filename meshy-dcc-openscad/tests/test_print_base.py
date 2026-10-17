"""meshy_openscad__write_print_base: mesh bounds and the generated source."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from meshy_dcc_openscad import print_base

TRIANGLE = [(0, 0, 0), (2, 0, 0), (0, 4, 6)]


def _binary_stl(path: Path) -> Path:
    body = struct.pack("<12fH", 0, 0, 1, *TRIANGLE[0], *TRIANGLE[1], *TRIANGLE[2], 0)
    path.write_bytes(b"\0" * 80 + struct.pack("<I", 1) + body)
    return path


def test_bounds_of_binary_and_ascii_stl(tmp_path):
    ascii_stl = tmp_path / "a.stl"
    ascii_stl.write_text(
        "solid t\nfacet normal 0 0 1\nouter loop\n"
        + "".join("vertex %s %s %s\n" % point for point in TRIANGLE)
        + "endloop\nendfacet\nendsolid t\n",
        encoding="ascii",
    )
    expected = ([0, 0, 0], [2, 4, 6])
    assert print_base.stl_bounds(_binary_stl(tmp_path / "b.stl")) == expected
    assert print_base.stl_bounds(ascii_stl) == expected


def test_y_up_bounds_follow_the_rotation():
    # rotate([90, 0, 0]): (x, y, z) -> (x, -z, y)
    assert print_base._y_up([0, 0, 0], [2, 4, 6]) == ([0, -6, 0], [2, 0, 4])


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHY_DCC_OPENSCAD_ALLOWED_ROOTS", str(tmp_path))
    (tmp_path / "meshy").mkdir()
    return tmp_path


def test_writes_a_new_parametric_source(workspace):
    mesh = _binary_stl(workspace / "meshy" / "cat.stl")
    result = print_base.write_print_base(
        str(workspace / "cat_base.scad"), str(mesh), target_height=60, up_axis="y"
    )

    source = (workspace / "cat_base.scad").read_text(encoding="utf-8")
    assert 'mesh_file = "meshy/cat.stl";' in source
    assert 'up_axis = "y";' in source and "target_height = 60.0;" in source
    assert "y_up_min = [0.0, -6.0, 0.0];" in source and "y_up_max = [2.0, 0.0, 4.0];" in source
    assert result["scale"] == 15.0 and result["model_size"] == [30.0, 90.0, 60.0]
    assert "adapter_checked_references" in result["verified"]
    with pytest.raises(FileExistsError):
        print_base.write_print_base(str(workspace / "cat_base.scad"), str(mesh))


def test_refuses_a_mesh_outside_the_workspace(workspace, tmp_path_factory):
    outside = _binary_stl(tmp_path_factory.mktemp("elsewhere") / "x.stl")
    with pytest.raises(ValueError, match="workspace"):
        print_base.write_print_base(str(workspace / "x.scad"), str(outside))


def test_refuses_sinking_deeper_than_the_base(workspace):
    mesh = _binary_stl(workspace / "meshy" / "cat.stl")
    with pytest.raises(ValueError, match="sink"):
        print_base.write_print_base(str(workspace / "x.scad"), str(mesh), base_height=1, sink=2)
