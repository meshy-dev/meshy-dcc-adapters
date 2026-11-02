@tool
extends EditorPlugin

const Commands = preload("res://addons/meshy_dcc_godot/commands.gd")

var _failures: Array[String] = []


func _enter_tree() -> void:
	call_deferred("_run")


func _run() -> void:
	EditorInterface.open_scene_from_path("res://main.tscn")
	await get_tree().process_frame
	var commands = Commands.new(self)
	for method in ["scene.set_property", "capability.update_property"]:
		var node := EditorInterface.get_edited_scene_root().get_node("RedBox") as Node3D
		node.position = Vector3(9, 8, 7)
		var manager := get_undo_redo()
		var history := manager.get_history_undo_redo(manager.get_object_history_id(node))
		for invalid in [
			"Vector3(-2.2, 1.5, 0)", null, [1, 2], [1, 2, 3, 4],
			[1, "bad", 3], [1, true, 3], [1, NAN, 3],
			{"x": "bad", "y": 2, "z": 3}, {"x": 1, "typo": 2},
		]:
			var previous := node.position
			var version := history.get_version()
			var refused: Dictionary = commands.execute(method, {
				"node_path": "RedBox", "property": "position", "value": invalid,
			})
			_expect(refused.has("__error__"), "%s accepted invalid Vector3: %s" % [method, invalid])
			_expect(node.position == previous, "%s changed position for invalid input" % method)
			_expect(history.get_version() == version, "%s recorded undo for invalid input" % method)
		var applied: Dictionary = commands.execute(method, JSON.parse_string(JSON.stringify({
			"node_path": "RedBox", "property": "position", "value": [-2.2, 1.5, 0],
		})))
		_expect(applied.get("updated") == true, "%s did not accept a numeric array" % method)
		_expect(node.position.is_equal_approx(Vector3(-2.2, 1.5, 0)), "%s did not store the requested array" % method)
		_expect_readback(applied, node.position, method)
		history.undo()
		_expect(node.position.is_equal_approx(Vector3(9, 8, 7)), "%s undo did not restore the previous value" % method)
		history.redo()
		_expect(node.position.is_equal_approx(Vector3(-2.2, 1.5, 0)), "%s redo did not restore the requested value" % method)
		applied = commands.execute(method, {
			"node_path": "RedBox", "property": "position", "value": {"x": 3, "y": 2, "z": 1},
		})
		_expect(node.position.is_equal_approx(Vector3(3, 2, 1)), "%s did not store the numeric object" % method)
		_expect_readback(applied, node.position, method)
		applied = commands.execute(method, {
			"node_path": "RedBox", "property": "position", "value": {"y": 4},
		})
		_expect(node.position.is_equal_approx(Vector3(3, 4, 1)), "%s did not preserve unspecified object components" % method)
		_expect_readback(applied, node.position, method)
		_expect(EditorInterface.save_scene() == OK, "%s could not save the scene" % method)
		EditorInterface.reload_scene_from_path("res://main.tscn")
		await get_tree().process_frame
		node = EditorInterface.get_edited_scene_root().get_node("RedBox") as Node3D
		_expect(node.position.is_equal_approx(Vector3(3, 4, 1)), "%s save/reopen lost the property" % method)
	if _failures.is_empty():
		print("SCENE_PROPERTY_SMOKE_OK")
	get_tree().quit(0 if _failures.is_empty() else 1)


func _expect_readback(result: Dictionary, stored: Vector3, method: String) -> void:
	var value = result.get("value")
	_expect(value is Array and value.size() == 3, "%s did not return structured native readback" % method)
	if value is Array and value.size() == 3:
		_expect(Vector3(value[0], value[1], value[2]).is_equal_approx(stored), "%s readback differs from the stored property" % method)


func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
