"""Import an asset descriptor into the current 3ds Max scene."""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from dcc_mcp_core.asset_import import (
    AssetDescriptor,
    AssetFileVariant,
    AssetImportValidationError,
    AxisHint,
    ImportToSceneRequest,
    ImportToSceneResult,
    ImportWarning,
    ImportWarningCode,
    MaterialMode,
    UnitHint,
)

from dcc_mcp_3dsmax._display_utils import assign_nodes_to_layer
from dcc_mcp_3dsmax._scene_utils import iter_scene_nodes
from dcc_mcp_3dsmax.api import get_runtime, with_max

_FORMAT_PRIORITY = ("fbx", "obj", "3ds")


@with_max
def main(request: Any) -> Dict[str, Any]:
    """Import one asset request and return a serialized ImportToSceneResult."""
    try:
        request_obj = _coerce_request(request)
        request_obj.descriptor.validate()
    except (AssetImportValidationError, KeyError, TypeError, ValueError) as exc:
        return _envelope(
            ImportToSceneResult(success=False, error_message=str(exc)),
            message="Import request validation failed",
        )

    runtime = get_runtime()
    before = _scene_keys(iter_scene_nodes(runtime))
    warnings: List[ImportWarning] = []

    if request_obj.skip_existing and _scene_contains_asset(runtime, request_obj.descriptor.asset_id):
        result = ImportToSceneResult(
            success=True,
            imported_nodes=[],
            warnings=[],
            extra={"asset_id": request_obj.descriptor.asset_id, "skipped": True},
        )
        return _envelope(result, message="Skipped already-imported asset")

    variant, format_name = _choose_variant(request_obj.descriptor.variants)
    if variant is None or format_name is None:
        return _envelope(
            ImportToSceneResult(success=False, error_message="No supported asset variant was found"),
            message="Import request validation failed",
        )

    dispatch_result = _dispatch_import(runtime, variant, format_name, request_obj, warnings)
    if not dispatch_result.get("success"):
        return _envelope(
            ImportToSceneResult(
                success=False,
                warnings=warnings,
                error_message=str(dispatch_result.get("message") or "Asset import failed"),
                extra={"import_response": dict(dispatch_result)},
            ),
            message=str(dispatch_result.get("message") or "Asset import failed"),
        )

    data = dispatch_result.get("data") if isinstance(dispatch_result, Mapping) else {}
    dispatch_data = data if isinstance(data, Mapping) else {}
    warnings.extend(_warnings_from_result(dispatch_data))
    imported_nodes = _new_scene_nodes(runtime, before)
    if not imported_nodes and dispatch_data.get("created_nodes"):
        imported_nodes = _resolve_nodes_by_name(runtime, dispatch_data["created_nodes"])

    warnings.extend(
        _apply_post_import_overrides(
            runtime,
            imported_nodes,
            request_obj,
            format_name,
        )
    )

    result = ImportToSceneResult(
        success=True,
        imported_nodes=[str(getattr(node, "name", "")) for node in imported_nodes if getattr(node, "name", "")],
        warnings=warnings,
        extra={
            "asset_id": request_obj.descriptor.asset_id,
            "variant": _variant_summary(variant),
            "format": format_name,
            "material_mode": request_obj.material_mode,
            "target_collection": request_obj.target_collection,
            "skip_existing": bool(request_obj.skip_existing),
        },
    )
    return _envelope(result, message="Imported asset to scene")


def _coerce_request(request: Any) -> ImportToSceneRequest:
    if isinstance(request, ImportToSceneRequest):
        return request
    if isinstance(request, Mapping):
        return ImportToSceneRequest.from_dict(request)
    raise TypeError("request must be an ImportToSceneRequest or mapping")


def _dispatch_import(
    runtime: Any,
    variant: AssetFileVariant,
    format_name: str,
    request: ImportToSceneRequest,
    warnings: List[ImportWarning],
) -> Dict[str, Any]:
    action_name = "action_import_fbx.py" if format_name == "fbx" else "action_import_geometry.py"
    module = _load_action_module(action_name)

    if format_name == "fbx":
        units = _fbx_units(request.descriptor)
        up_axis = _fbx_up_axis(request.descriptor)
        mode = request.extra.get("fbx_mode", request.extra.get("mode", "merge"))
        return module.main(
            file_path=str(variant.local_path),
            mode=str(mode),
            units=units,
            up_axis=up_axis,
            include_animation=bool(request.extra.get("include_animation", True)),
        )

    if request.descriptor.up_axis == AxisHint.Y:
        warnings.append(
            ImportWarning(
                code=ImportWarningCode.UNSUPPORTED_FEATURE,
                message="Applied a best-effort Y-up to Z-up remap after import",
                detail="format={}, source_up_axis=y".format(format_name),
            )
        )

    return module.main(
        file_path=str(variant.local_path),
        format=format_name,
        mode=str(request.extra.get("mode", "merge")),
    )


def _apply_post_import_overrides(
    runtime: Any,
    imported_nodes: Sequence[Any],
    request: ImportToSceneRequest,
    format_name: str,
) -> List[ImportWarning]:
    warnings: List[ImportWarning] = []
    if not imported_nodes:
        return warnings

    scale = request.descriptor.scale_hint
    if scale is None and request.descriptor.meters_per_unit not in (None, 1.0):
        scale = float(request.descriptor.meters_per_unit)
    if scale is not None and scale != 1.0 and format_name != "fbx":
        _apply_uniform_scale(runtime, imported_nodes, scale)

    if request.descriptor.up_axis == AxisHint.Y and format_name != "fbx":
        _apply_rotation(runtime, imported_nodes, [90.0, 0.0, 0.0])

    placement = request.placement
    if placement is not None:
        if placement.translate is not None:
            _apply_translation(runtime, imported_nodes, placement.translate)
        if placement.rotate is not None:
            _apply_rotation(runtime, imported_nodes, placement.rotate)
        if placement.scale is not None:
            _apply_scale(runtime, imported_nodes, placement.scale)
        if placement.parent_name:
            _apply_parent(runtime, imported_nodes, placement.parent_name, warnings)

    if request.target_collection:
        try:
            layer_result = assign_nodes_to_layer(
                runtime,
                layer_name=request.target_collection,
                nodes=imported_nodes,
                create_if_missing=True,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ImportWarning(
                    code=ImportWarningCode.UNSUPPORTED_FEATURE,
                    message="Could not assign imported nodes to target_collection",
                    detail=str(exc),
                )
            )
        else:
            warnings.extend(_warnings_from_result(layer_result))

    warnings.extend(_material_mode_overrides(runtime, imported_nodes, request.material_mode))
    return warnings


def _material_mode_overrides(runtime: Any, nodes: Sequence[Any], material_mode: str) -> List[ImportWarning]:
    mode = str(material_mode or MaterialMode.AS_AUTHORED)
    if mode == MaterialMode.AS_AUTHORED:
        return []

    warnings: List[ImportWarning] = []
    if mode == MaterialMode.SKIP:
        for node in nodes:
            try:
                node.material = None
            except Exception:  # noqa: BLE001
                warnings.append(
                    ImportWarning(
                        code=ImportWarningCode.UNSUPPORTED_FEATURE,
                        message="Could not clear an imported material",
                        detail=str(getattr(node, "name", "")),
                    )
                )
        return warnings

    gray = _make_gray_material(runtime)
    if gray is None:
        return [
            ImportWarning(
                code=ImportWarningCode.MATERIAL_FALLBACK,
                message="Could not create a gray fallback material",
                detail=mode,
            )
        ]

    for node in nodes:
        try:
            node.material = gray
        except Exception:  # noqa: BLE001
            warnings.append(
                ImportWarning(
                    code=ImportWarningCode.UNSUPPORTED_FEATURE,
                    message="Could not assign a gray fallback material",
                    detail=str(getattr(node, "name", "")),
                )
            )
    return warnings


def _make_gray_material(runtime: Any) -> Any:
    for attr in ("StandardMaterial", "PhysicalMaterial"):
        factory = getattr(runtime, attr, None)
        if not callable(factory):
            continue
        try:
            material = factory()
        except Exception:  # noqa: BLE001
            continue
        for prop in ("diffuse", "base_color"):
            if hasattr(material, prop):
                try:
                    setattr(material, prop, [128.0, 128.0, 128.0])
                except Exception:  # noqa: BLE001
                    pass
        return material
    return None


def _apply_translation(runtime: Any, nodes: Sequence[Any], value: Sequence[float]) -> None:
    point = _point3(runtime, value)
    for node in nodes:
        try:
            node.pos = point
        except Exception:  # noqa: BLE001
            pass


def _apply_rotation(runtime: Any, nodes: Sequence[Any], value: Sequence[float]) -> None:
    rotation = _rotation_value(runtime, value)
    for node in nodes:
        try:
            node.rotation = rotation
        except Exception:  # noqa: BLE001
            pass


def _apply_uniform_scale(runtime: Any, nodes: Sequence[Any], factor: float) -> None:
    scale = _point3(runtime, [factor, factor, factor])
    for node in nodes:
        try:
            node.scale = scale
        except Exception:  # noqa: BLE001
            pass


def _apply_scale(runtime: Any, nodes: Sequence[Any], value: Sequence[float]) -> None:
    scale = _point3(runtime, value)
    for node in nodes:
        try:
            node.scale = scale
        except Exception:  # noqa: BLE001
            pass


def _apply_parent(runtime: Any, nodes: Sequence[Any], parent_name: str, warnings: List[ImportWarning]) -> None:
    parent = None
    try:
        parent = runtime.getNodeByName(parent_name)
    except Exception:  # noqa: BLE001
        parent = None
    if parent is None:
        warnings.append(
            ImportWarning(
                code=ImportWarningCode.UNKNOWN,
                message="Could not resolve parent_name for imported nodes",
                detail=parent_name,
            )
        )
        return
    for node in nodes:
        try:
            node.parent = parent
        except Exception:  # noqa: BLE001
            warnings.append(
                ImportWarning(
                    code=ImportWarningCode.UNSUPPORTED_FEATURE,
                    message="Could not parent imported node",
                    detail=str(getattr(node, "name", "")),
                )
            )


def _choose_variant(variants: Sequence[AssetFileVariant]) -> Tuple[Optional[AssetFileVariant], Optional[str]]:
    ranked = sorted(enumerate(variants), key=lambda item: _variant_sort_key(item[0], item[1]))
    for _index, variant in ranked:
        format_name = _variant_format(variant)
        if format_name is not None:
            return variant, format_name
    return None, None


def _variant_sort_key(index: int, variant: AssetFileVariant) -> Tuple[int, int, int]:
    format_name = _variant_format(variant)
    format_rank = _FORMAT_PRIORITY.index(format_name) if format_name in _FORMAT_PRIORITY else len(_FORMAT_PRIORITY)
    return (0 if variant.preferred else 1, format_rank, index)


def _variant_format(variant: AssetFileVariant) -> Optional[str]:
    format_name = str(getattr(variant, "format", "") or "").lower()
    if format_name in _FORMAT_PRIORITY:
        return format_name
    suffix = Path(str(variant.local_path)).suffix.lower().lstrip(".")
    return suffix if suffix in _FORMAT_PRIORITY else None


def _variant_summary(variant: AssetFileVariant) -> Dict[str, Any]:
    return {
        "local_path": str(variant.local_path),
        "format": _variant_format(variant),
        "preferred": bool(variant.preferred),
        "mime": variant.mime,
    }


def _fbx_units(descriptor: AssetDescriptor) -> Optional[str]:
    mapping = {
        UnitHint.METER: "m",
        UnitHint.CENTIMETER: "cm",
        UnitHint.INCH: "in",
    }
    return mapping.get(descriptor.unit_hint)


def _fbx_up_axis(descriptor: AssetDescriptor) -> Optional[str]:
    if descriptor.up_axis.lower() == AxisHint.Y:
        return "Y"
    if descriptor.up_axis.lower() == AxisHint.Z:
        return "Z"
    return None


def _point3(runtime: Any, value: Sequence[float]) -> Any:
    factory = getattr(runtime, "Point3", None) or getattr(runtime, "point3", None)
    if callable(factory):
        return factory(float(value[0]), float(value[1]), float(value[2]))
    return [float(value[0]), float(value[1]), float(value[2])]


def _rotation_value(runtime: Any, value: Sequence[float]) -> Any:
    factory = getattr(runtime, "eulerAngles", None) or getattr(runtime, "EulerAngles", None)
    if callable(factory):
        try:
            return factory(float(value[0]), float(value[1]), float(value[2]))
        except TypeError:
            return factory([float(value[0]), float(value[1]), float(value[2])])
    factory = getattr(runtime, "quat", None)
    if callable(factory):
        try:
            return factory(float(value[0]), float(value[1]), float(value[2]), 0.0)
        except TypeError:
            return factory([float(value[0]), float(value[1]), float(value[2]), 0.0])
    return [float(value[0]), float(value[1]), float(value[2])]


def _new_scene_nodes(runtime: Any, before: set) -> List[Any]:
    nodes = []
    for node in iter_scene_nodes(runtime):
        if _node_key(node) not in before:
            nodes.append(node)
    return nodes


def _resolve_nodes_by_name(runtime: Any, identities: Sequence[Mapping[str, Any]]) -> List[Any]:
    nodes = []
    seen = set()
    for identity in identities:
        name = str(identity.get("node_name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            node = runtime.getNodeByName(name)
        except Exception:  # noqa: BLE001
            node = None
        if node is not None:
            nodes.append(node)
    return nodes


def _scene_keys(nodes: Iterable[Any]) -> set:
    return {_node_key(node) for node in nodes}


def _node_key(node: Any) -> Tuple[Optional[int], str]:
    handle = getattr(node, "handle", None)
    try:
        object_id = int(handle) if handle is not None else None
    except (TypeError, ValueError):
        object_id = None
    return object_id, str(getattr(node, "name", ""))


def _scene_contains_asset(runtime: Any, asset_id: str) -> bool:
    for node in iter_scene_nodes(runtime):
        if str(getattr(node, "name", "")) == str(asset_id):
            return True
        custom = getattr(node, "custom_properties", None) or getattr(node, "user_properties", None) or {}
        if isinstance(custom, Mapping) and str(custom.get("asset_id") or custom.get("dcc_asset_id") or "") == asset_id:
            return True
        if str(getattr(node, "asset_id", "")) == asset_id:
            return True
    return False


def _warnings_from_result(result: Mapping[str, Any]) -> List[ImportWarning]:
    warnings: List[ImportWarning] = []
    for entry in result.get("warnings", []) or []:
        if isinstance(entry, Mapping):
            warnings.append(
                ImportWarning(
                    code=str(entry.get("code", ImportWarningCode.UNKNOWN)),
                    message=str(entry.get("message", "")),
                    detail=entry.get("detail"),
                )
            )
        else:
            warnings.append(ImportWarning(code=ImportWarningCode.UNKNOWN, message=str(entry)))
    return warnings


def _envelope(result: ImportToSceneResult, *, message: str) -> Dict[str, Any]:
    status = "success" if result.success else "error"
    return {
        "success": result.success,
        "status": status,
        "message": message if result.success else (result.error_message or message),
        "data": result.to_dict(),
    }


@lru_cache(maxsize=None)
def _load_action_module(script_name: str):
    path = Path(__file__).with_name(script_name)
    module_name = "_dcc_mcp_3dsmax_{}".format(path.stem)
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError("Could not load {}".format(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
