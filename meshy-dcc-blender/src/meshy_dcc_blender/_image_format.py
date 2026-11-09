"""Image output format changes across Blender's media-type API.

Blender 5 filters the ``file_format`` enum by ``image_settings.media_type``, so
``OPEN_EXR_MULTILAYER`` can only be assigned after the media type is
``MULTI_LAYER_IMAGE``. Older builds have no ``media_type`` and take the format
directly.
"""

from __future__ import annotations

from typing import Any

_MULTILAYER_FORMAT = "OPEN_EXR_MULTILAYER"


def media_type_for_format(file_format: str) -> str:
    if file_format == _MULTILAYER_FORMAT:
        return "MULTI_LAYER_IMAGE"
    return "VIDEO" if file_format == "FFMPEG" else "IMAGE"


def set_image_format(settings: Any, file_format: str) -> None:
    """Set the media type (when the build has one) before the file format.

    A rejected format restores the previous pair: switching the media type can
    reset the format before the format setter refuses an unavailable container.
    No other container is ever substituted.
    """
    name = str(file_format).strip().upper()
    previous_format = settings.file_format
    previous_media = getattr(settings, "media_type", None)
    try:
        if previous_media is not None:
            settings.media_type = media_type_for_format(name)
        settings.file_format = name
    except Exception:
        if previous_media is not None:
            settings.media_type = previous_media
        settings.file_format = previous_format
        raise
