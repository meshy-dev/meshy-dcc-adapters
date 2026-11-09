"""Structural PNG completeness checks."""

from __future__ import annotations

import struct

import pytest

from meshy_dcc_blender._png_integrity import is_complete_png
from tests.test_render_jobs import _chunk, png_bytes


def _check(tmp_path, data):
    path = tmp_path / "frame.png"
    path.write_bytes(data)
    return is_complete_png(path)


def test_a_complete_png_passes(tmp_path):
    assert _check(tmp_path, png_bytes()) is True


@pytest.mark.parametrize("cut", [1, 5, 12, 20, 40])
def test_truncation_is_rejected(tmp_path, cut):
    assert _check(tmp_path, png_bytes()[:-cut]) is False


def test_a_flipped_data_byte_fails_its_checksum(tmp_path):
    data = bytearray(png_bytes())
    data[-20] ^= 0xFF  # inside IDAT
    assert _check(tmp_path, bytes(data)) is False


def test_trailing_bytes_after_iend_are_rejected(tmp_path):
    assert _check(tmp_path, png_bytes() + b"\x00") is False


def test_signature_only_and_zero_filled_files_are_rejected(tmp_path):
    assert _check(tmp_path, b"\x89PNG\r\n\x1a\n") is False
    assert _check(tmp_path, b"\x89PNG\r\n\x1a\n" + b"\x00" * 64) is False


def test_structure_must_start_with_ihdr_and_contain_image_data(tmp_path):
    magic = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    assert _check(tmp_path, magic + _chunk(b"IDAT", b"x") + _chunk(b"IEND")) is False
    assert _check(tmp_path, magic + _chunk(b"IHDR", header) + _chunk(b"IEND")) is False


def test_a_missing_file_is_not_complete(tmp_path):
    assert is_complete_png(tmp_path / "absent.png") is False
