"""Bounded PNG completeness check without bpy or an image library.

Walks the chunk structure and checks every CRC, that the first chunk is IHDR,
that image data exists, and that the file ends exactly at a closing IEND chunk.
That catches a truncated or partly written frame, which a leading signature
cannot. It does not inflate the image data, so a stream that is internally
corrupt but correctly checksummed is not detected. Memory stays bounded by the
block size.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

_MAGIC = b"\x89PNG\r\n\x1a\n"
_BLOCK = 64 * 1024


def is_complete_png(path: Path) -> bool:
    """Return whether ``path`` is a structurally complete PNG file."""
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            if stream.read(8) != _MAGIC:
                return False
            first = True
            has_image_data = False
            while True:
                header = stream.read(8)
                if len(header) != 8:
                    return False
                length, kind = struct.unpack(">I4s", header)
                if length > 0x7FFFFFFF or stream.tell() + length + 4 > size:
                    return False
                # IHDR opens the file and may not appear again.
                if (kind == b"IHDR") != first or (first and length != 13):
                    return False
                first = False
                crc = zlib.crc32(kind)
                remaining = length
                while remaining:
                    block = stream.read(min(remaining, _BLOCK))
                    if not block:
                        return False
                    remaining -= len(block)
                    crc = zlib.crc32(block, crc)
                if stream.read(4) != struct.pack(">I", crc & 0xFFFFFFFF):
                    return False
                has_image_data = has_image_data or kind == b"IDAT"
                if kind == b"IEND":
                    return length == 0 and has_image_data and stream.tell() == size
    except OSError:
        return False
