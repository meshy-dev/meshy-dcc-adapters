@tool
extends RefCounted

const IMPORT_ROOT := "res://assets/meshy/"

var _plugin: EditorPlugin
var _import_depth := 0


func _init(plugin: EditorPlugin) -> void:
	_plugin = plugin
	var filesystem := EditorInterface.get_resource_filesystem()
	filesystem.resources_reimporting.connect(_import_started)
	filesystem.resources_reimported.connect(_import_finished)


func _import_started(_paths: PackedStringArray) -> void:
	_import_depth += 1


func _import_finished(_paths: PackedStringArray) -> void:
	_import_depth = maxi(0, _import_depth - 1)


func _is_importing() -> bool:
	# Nested texture imports can clear Godot's flag before the outer GLB finishes.
	return _import_depth > 0 or EditorInterface.get_resource_filesystem().is_importing()


func session(params: Dictionary = {}) -> Dictionary:
	var workspace := ProjectSettings.globalize_path("res://").trim_suffix("/")
	# Set by `meshy-dcc start-instance` for the project it opened.
	var configured_workspace := OS.get_environment("MESHY_DCC_START_PROJECT").trim_suffix("/")
	if not configured_workspace.is_empty() and configured_workspace != workspace:
		return _error("The start-instance project does not match the open Godot project")
	var scene := EditorInterface.get_edited_scene_root()
	var unsaved := _unsaved()
	var result := {
		"host_pid": OS.get_process_id(),
		"workspace": workspace,
		"scene": scene.scene_file_path if scene else "",
		"engine_version": Engine.get_version_info().get("string", "unknown"),
		"dirty": null if unsaved == null else not (unsaved as Array).is_empty(),
		"unsaved": unsaved,
		"filesystem_scanning": EditorInterface.get_resource_filesystem().is_scanning(),
		"filesystem_importing": _is_importing(),
	}
	var asset_path := str(params.get("asset_path", ""))
	if not asset_path.is_empty():
		var checked := _asset_path(asset_path)
		if checked.has("__error__"):
			return checked
		result["asset_ready"] = _asset_ready(checked.path)
	return result


func _asset_ready(asset_path: String) -> bool:
	var filesystem := EditorInterface.get_resource_filesystem()
	if filesystem.is_scanning() or _is_importing():
		return false
	var directory := filesystem.get_filesystem_path(asset_path.get_base_dir())
	if directory == null:
		return false
	var index := directory.find_file_index(asset_path.get_file())
	return index >= 0 and directory.get_file_type(index) == "PackedScene" and directory.get_file_import_is_valid(index)


# Unsaved scene and script paths, or null when this Godot cannot report them.
func _unsaved() -> Variant:
	var script_editor := EditorInterface.get_script_editor()
	if not EditorInterface.has_method("get_unsaved_scenes") \
		or script_editor == null or not script_editor.has_method("get_unsaved_files"):
		return null
	var paths: Array[String] = []
	for path in EditorInterface.call("get_unsaved_scenes"):
		paths.append(str(path) if not str(path).is_empty() else "(new scene)")
	for path in script_editor.call("get_unsaved_files"):
		paths.append(str(path))
	return paths


func quit(params: Dictionary) -> Dictionary:
	var current := session()
	if current.has("__error__"):
		return current
	if int(params.get("expected_pid", -1)) != int(current.host_pid):
		return _error("Refusing to quit a different Godot Editor process")
	if str(params.get("workspace", "")) != str(current.workspace):
		return _error("Refusing to quit a different Godot project")
	if current.dirty != false and params.get("discard_unsaved", false) != true:
		return _error("Godot has unsaved changes or cannot report them; authorize discard before quitting")
	_plugin.call_deferred("_meshy_core_quit")
	return {"quit_requested": true, "host_pid": current.host_pid, "workspace": current.workspace}


func prepare_asset(params: Dictionary) -> Dictionary:
	var checked := _asset_path(str(params.get("path", "")))
	if checked.has("__error__"):
		return checked
	var filesystem := EditorInterface.get_resource_filesystem()
	var already_scanning := filesystem.is_scanning()
	var already_importing := _is_importing()
	# Godot pumps _process while importing; a nested scan can re-enter reimport.
	if not already_scanning and not already_importing:
		filesystem.scan()
	return {"scan_started": not already_scanning and not already_importing,
		"filesystem_scanning": already_scanning, "filesystem_importing": already_importing, "path": checked.path}


func import_model(params: Dictionary) -> Dictionary:
	var checked := _asset_path(str(params.get("path", "")))
	if checked.has("__error__"):
		return checked
	if not _asset_ready(checked.path):
		return _error("Godot is still importing the project files; wait for session.asset_ready before instantiating")
	var resource := ResourceLoader.load(checked.path)
	if not resource is PackedScene:
		return _error("Godot did not import this GLB as a PackedScene")
	var scene_root := EditorInterface.get_edited_scene_root()
	if scene_root == null:
		return _error("Open a scene before importing the GLB")
	var instance := (resource as PackedScene).instantiate()
	if not instance is Node3D:
		instance.free()
		return _error("Imported GLB root is not a Node3D")
	var requested_name := str(params.get("name", "")).strip_edges()
	if requested_name.is_empty():
		requested_name = checked.path.get_file().get_basename()
	if requested_name.length() > 128 or "/" in requested_name or "\\" in requested_name or requested_name in [".", ".."]:
		instance.free()
		return _error("Model name must be a single node name")
	if scene_root.get_node_or_null(NodePath(requested_name)) != null:
		instance.free()
		return _error("A node with that name already exists in the active scene")
	instance.name = requested_name

	var undo := _plugin.get_undo_redo()
	undo.create_action("Meshy: Import GLB")
	undo.add_do_method(scene_root, "add_child", instance)
	undo.add_do_method(self, "_set_scene_owner", instance, scene_root)
	undo.add_undo_method(scene_root, "remove_child", instance)
	undo.add_do_reference(instance)
	undo.commit_action()

	if instance.get_parent() != scene_root:
		return _error("Godot did not attach the imported model to the active scene")
	var readback := _snapshot(instance)
	if int(readback.get("mesh_instance_count", 0)) < 1:
		return _error("Imported GLB scene contains no readable MeshInstance3D nodes")
	return {
		"host_pid": OS.get_process_id(),
		"workspace": ProjectSettings.globalize_path("res://").trim_suffix("/"),
		"asset_path": checked.path,
		"scene_path": scene_root.scene_file_path,
		"object": readback,
		"saved": false,
	}


func inspect_model(params: Dictionary) -> Dictionary:
	var node_path := str(params.get("node_path", ""))
	if not node_path.is_empty():
		var scene_root := EditorInterface.get_edited_scene_root()
		if scene_root == null:
			return _error("No scene is open")
		var node := scene_root.get_node_or_null(NodePath(node_path))
		if node == null:
			return _error("Imported model node was not found in the current scene")
		return {
			"host_pid": OS.get_process_id(),
			"workspace": ProjectSettings.globalize_path("res://").trim_suffix("/"),
			"scene_path": scene_root.scene_file_path,
			"object": _snapshot(node),
		}

	var checked := _asset_path(str(params.get("path", "")))
	if checked.has("__error__"):
		return checked
	if not _asset_ready(checked.path):
		return {"ready": false, "filesystem_scanning": EditorInterface.get_resource_filesystem().is_scanning(),
			"filesystem_importing": _is_importing(), "path": checked.path}
	var resource := ResourceLoader.load(checked.path)
	if not resource is PackedScene:
		return {"ready": false, "filesystem_scanning": false, "path": checked.path}
	var instance := (resource as PackedScene).instantiate()
	if instance == null:
		return _error("Godot could not instantiate the imported GLB for inspection")
	var result := {"ready": true, "path": checked.path, "object": _snapshot(instance)}
	instance.free()
	return result


func _asset_path(raw: String) -> Dictionary:
	if not raw.begins_with(IMPORT_ROOT) or not raw.to_lower().ends_with(".glb") or "\\" in raw:
		return _error("Use a GLB below res://assets/meshy/")
	var relative := raw.trim_prefix("res://")
	for part in relative.split("/"):
		if part.is_empty() or part == "." or part == "..":
			return _error("GLB path cannot contain empty or traversal segments")
	if not FileAccess.file_exists(raw):
		return _error("GLB file does not exist in this project")
	return {"path": raw}


func _set_scene_owner(node: Node, owner: Node) -> void:
	if node != owner:
		node.owner = owner


func _snapshot(root: Node, object_root: Node3D = null, bounds: Dictionary = {}) -> Dictionary:
	var is_object_root := false
	if object_root == null and root is Node3D:
		object_root = root as Node3D
		is_object_root = true
	elif root == object_root:
		is_object_root = true
	var result := {
		"name": root.name,
		"type": root.get_class(),
		"path": str(root.get_path()) if root.is_inside_tree() else "",
		"children": [],
		"mesh_instance_count": 0,
		"surface_count": 0,
		"vertex_count": 0,
		"triangle_count": 0,
		"materials": [],
	}
	if root is Node3D:
		result["transform"] = _transform(root as Node3D)
	if root is MeshInstance3D:
		var mesh_node := root as MeshInstance3D
		var mesh_result := _mesh_snapshot(mesh_node)
		result["mesh"] = mesh_result
		result["mesh_instance_count"] = 1
		result["surface_count"] = mesh_result.surface_count
		result["vertex_count"] = mesh_result.vertex_count
		result["triangle_count"] = mesh_result.triangle_count
		result["materials"] = mesh_result.materials.duplicate(true)
		if object_root != null and mesh_node.mesh != null:
			_collect_bounds(mesh_node, object_root, bounds)
	for child in root.get_children():
		var child_snapshot := _snapshot(child, object_root, bounds)
		result["children"].append(child_snapshot)
		result["mesh_instance_count"] += int(child_snapshot.mesh_instance_count)
		result["surface_count"] += int(child_snapshot.surface_count)
		result["vertex_count"] += int(child_snapshot.vertex_count)
		result["triangle_count"] += int(child_snapshot.triangle_count)
		result["materials"].append_array(child_snapshot.materials)
	if is_object_root:
		result["bounds"] = _bounds_snapshot(bounds)
	return result


func _mesh_snapshot(node: MeshInstance3D) -> Dictionary:
	var mesh := node.mesh
	var output := {"class": mesh.get_class() if mesh else "null", "surface_count": 0,
		"vertex_count": 0, "triangle_count": 0, "materials": [], "bounds_node_local": null,
		"bounds_global": null}
	if mesh == null:
		return output
	output.bounds_node_local = _aabb_snapshot(mesh.get_aabb())
	if node.is_inside_tree():
		output.bounds_global = _aabb_snapshot(node.global_transform * mesh.get_aabb())
	output.surface_count = mesh.get_surface_count()
	for index in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(index)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		output.vertex_count += vertices.size()
		output.triangle_count += int(indices.size() / 3) if not indices.is_empty() else int(vertices.size() / 3)
		var material := node.get_surface_override_material(index)
		if material == null:
			material = mesh.surface_get_material(index)
		output.materials.append(_material_snapshot(material, index))
	return output


func _material_snapshot(material: Material, surface: int) -> Dictionary:
	var result := {"surface": surface, "class": material.get_class() if material else "null",
		"name": material.resource_name if material else ""}
	if material is BaseMaterial3D:
		var base := material as BaseMaterial3D
		result["albedo_color"] = [base.albedo_color.r, base.albedo_color.g, base.albedo_color.b, base.albedo_color.a]
		result["pbr"] = {
			"metallic": base.metallic,
			"roughness": base.roughness,
			"albedo_texture": _texture_ref(base.albedo_texture),
			"metallic_texture": _texture_ref(base.metallic_texture),
			"roughness_texture": _texture_ref(base.roughness_texture),
			"normal_texture": _texture_ref(base.normal_texture),
			"ao_texture": _texture_ref(base.ao_texture),
			"emission_enabled": base.emission_enabled,
			"emission_texture": _texture_ref(base.emission_texture),
		}
	return result


func _texture_ref(texture: Texture2D) -> Dictionary:
	if texture == null:
		return {"class": "null", "name": "", "path": ""}
	return {"class": texture.get_class(), "name": texture.resource_name, "path": texture.resource_path}


func _collect_bounds(node: MeshInstance3D, object_root: Node3D, bounds: Dictionary) -> void:
	if node.mesh == null:
		return
	var relative := Transform3D.IDENTITY
	if node != object_root:
		if object_root.is_inside_tree() and node.is_inside_tree():
			relative = object_root.global_transform.affine_inverse() * node.global_transform
		else:
			var current: Node = node
			while current != object_root:
				if not current is Node3D:
					return
				relative = (current as Node3D).transform * relative
				current = current.get_parent()
				if current == null:
					return
	var local_box: AABB = relative * node.mesh.get_aabb()
	_merge_aabb(bounds, "model_local", local_box)
	if object_root.is_inside_tree() and node.is_inside_tree():
		_merge_aabb(bounds, "global", node.global_transform * node.mesh.get_aabb())


func _merge_aabb(bounds: Dictionary, key: String, box: AABB) -> void:
	if bounds.has(key):
		var previous: AABB = bounds[key]
		bounds[key] = previous.merge(box)
	else:
		bounds[key] = box


func _bounds_snapshot(bounds: Dictionary) -> Dictionary:
	var result := {"model_local": null, "global": null}
	if bounds.has("model_local"):
		result.model_local = _aabb_snapshot(bounds.model_local)
	if bounds.has("global"):
		result.global = _aabb_snapshot(bounds.global)
	return result


func _aabb_snapshot(box: AABB) -> Dictionary:
	return {"position": _vector(box.position), "size": _vector(box.size), "end": _vector(box.end)}


func _transform(node: Node3D) -> Dictionary:
	var local := node.transform
	var in_tree := node.is_inside_tree()
	var global := node.global_transform if in_tree else local
	return {
		"local_position": _vector(local.origin),
		"local_rotation_degrees": _vector(node.rotation_degrees),
		"local_scale": _vector(local.basis.get_scale()),
		"global_position": _vector(global.origin),
		"global_rotation_degrees": _vector(node.global_rotation_degrees) if in_tree else _vector(node.rotation_degrees),
		"global_scale": _vector(global.basis.get_scale()),
		"global_transform_known": in_tree,
	}


func _vector(value: Vector3) -> Array[float]:
	return [value.x, value.y, value.z]


func _error(message: String) -> Dictionary:
	return {"__error__": message}
