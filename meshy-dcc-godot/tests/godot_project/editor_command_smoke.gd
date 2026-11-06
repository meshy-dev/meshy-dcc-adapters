@tool
extends EditorPlugin

const Commands = preload("res://addons/meshy_dcc_godot/commands.gd")
const RuntimePeer = preload("res://addons/meshy_dcc_godot/runtime_peer.gd")

var _failures: Array[String] = []


func _enter_tree() -> void:
	call_deferred("_run")


func _run() -> void:
	EditorInterface.open_scene_from_path("res://main.tscn")
	await get_tree().process_frame
	var commands = Commands.new(self)
	_packed_arrays(commands)
	_input_actions(commands)
	_validate_script(commands)
	_keyframes(commands)
	_selector_script_path()
	await _resource_preview(commands)
	_export_path(commands)
	if _failures.is_empty():
		print("EDITOR_COMMAND_SMOKE_OK")
	get_tree().quit(0 if _failures.is_empty() else 1)


func _packed_arrays(commands) -> void:
	var settings: Dictionary = commands.execute("capability.get_project_settings", {"prefix": "editor_plugins/enabled"})
	var enabled = settings.get("settings", {}).get("editor_plugins/enabled")
	_expect(enabled is Array and enabled.size() == 1, "PackedStringArray setting was not returned as an array: %s" % [enabled])
	var peer = RuntimePeer.new()
	var converted = peer._json_value({"names": PackedStringArray(["a", "b"]), "points": PackedVector2Array([Vector2(1, 2)]), "ints": PackedInt32Array([3])})
	_expect(converted == {"names": ["a", "b"], "points": [[1.0, 2.0]], "ints": [3]}, "runtime peer did not convert Packed arrays: %s" % [converted])
	peer.free()


func _input_actions(commands) -> void:
	var result: Dictionary = commands.execute("capability.set_input_action", {"action": "jump", "keycode": 32.0, "deadzone": 0.25})
	_expect(result.get("updated") == true and result.get("persisted") == true, "set_input_action did not report a persisted action: %s" % [result])
	_expect(_project_file().contains("jump={"), "project.godot has no jump action after set_input_action")
	_expect(ProjectSettings.has_setting("input/jump"), "input/jump missing from ProjectSettings")
	var again: Dictionary = commands.execute("capability.set_input_action", {"action": "jump", "keycode": 32})
	_expect(again.get("events", []).size() == 1 and again.get("deadzone") == 0.25, "repeating the same key duplicated it or reset the deadzone: %s" % [again])
	var more: Dictionary = commands.execute("capability.set_input_action", {"action": "jump", "keycode": 4194309})
	_expect(more.get("events", []).size() == 2, "a second key was not added: %s" % [more])
	var replaced: Dictionary = commands.execute("capability.set_input_action", {"action": "jump", "keycode": 4194309, "replace_events": true})
	_expect(replaced.get("events", []).size() == 1, "replace_events kept the old keys: %s" % [replaced])
	var spaced: Dictionary = commands.execute("capability.set_input_action", {"action": "fire weapon", "keycode": 70})
	_expect(spaced.get("persisted") == true, "an action name with a space was not persisted: %s" % [spaced])
	var listed: Dictionary = commands.execute("capability.get_input_actions", {})
	var names: Array = listed.get("actions", []).map(func(item): return item.name)
	_expect("jump" in names and "fire weapon" in names, "get_input_actions does not list the project actions: %s" % [names])
	_expect(not names.any(func(name): return str(name).begins_with("spatial_editor")), "get_input_actions listed editor shortcuts")
	for bad in [{"action": ""}, {"action": "a/b"}, {"action": "x", "deadzone": 2}, {"action": "x", "keycode": "A"}, {"action": "x", "keycode": 0}, {"action": "x", "keycode": 1.5}]:
		var refused: Dictionary = commands.execute("capability.set_input_action", bad)
		_expect(refused.has("__error__"), "set_input_action accepted %s" % [bad])
	_expect(not ProjectSettings.has_setting("input/x"), "a rejected request still wrote input/x")


func _validate_script(commands) -> void:
	var good: Dictionary = commands.execute("capability.validate_script", {"source": "extends Node\n"})
	_expect(good.get("valid") == true, "a valid script was rejected: %s" % [good])
	for blank in ["   ", "\n\t "]:
		for params in [{"source": blank}, {"source": blank, "path": "res://ok.gd"}]:
			var refused: Dictionary = commands.execute("capability.validate_script", params)
			_expect(refused.has("__error__"), "blank source %s was accepted: %s" % [params, refused])
	var from_path: Dictionary = commands.execute("capability.validate_script", {"path": "res://ok.gd"})
	_expect(from_path.get("valid") == true, "a path-only check failed: %s" % [from_path])
	var empty_with_path: Dictionary = commands.execute("capability.validate_script", {"source": "", "path": "res://ok.gd"})
	_expect(empty_with_path.get("valid") == true, "an empty source did not fall back to the path: %s" % [empty_with_path])
	_expect(commands.execute("capability.validate_script", {}).has("__error__"), "validate_script with nothing to check did not fail")


func _keyframes(commands) -> void:
	var root := EditorInterface.get_edited_scene_root()
	var player := AnimationPlayer.new()
	player.name = "Player"
	root.add_child(player)
	player.owner = root
	var animation := Animation.new()
	animation.length = 1.0
	animation.add_track(Animation.TYPE_POSITION_3D)
	animation.track_set_path(0, NodePath(".:position"))
	animation.add_track(Animation.TYPE_ROTATION_3D)
	animation.track_set_path(1, NodePath(".:rotation"))
	var library := AnimationLibrary.new()
	library.add_animation("run", library_animation(animation))
	player.add_animation_library("", library)
	var base := {"node_path": "Player", "animation": "run"}
	var ok: Dictionary = commands.execute("capability.set_animation_keyframe", base.merged({"track": 0, "time": 0.5, "value": [1, 2, 3]}))
	_expect(ok.get("inserted") == true and ok.get("key", -1) >= 0, "a position key was not inserted: %s" % [ok])
	_expect(animation.track_get_key_count(0) == 1 and animation.track_get_key_value(0, 0) == Vector3(1, 2, 3), "the stored position key is wrong")
	var rotated: Dictionary = commands.execute("capability.set_animation_keyframe", base.merged({"track": 1, "time": 0.0, "value": [0, 0, 0, 1]}))
	_expect(rotated.get("inserted") == true, "a unit quaternion key was not inserted: %s" % [rotated])
	for bad in [
		{"track": 7, "value": [0, 0, 0]}, {"track": 0.5, "value": [0, 0, 0]}, {"track": 0, "time": -1, "value": [0, 0, 0]},
		{"track": 0, "time": NAN, "value": [0, 0, 0]}, {"track": 0, "transition": INF, "value": [0, 0, 0]},
		{"track": 0}, {"track": 0, "value": [1, 2]}, {"track": 0, "value": [1, "x", 3]}, {"track": 0, "value": "up"},
		{"track": 1, "value": [0, 0, 0, 2]}, {"track": 1, "value": [0, 0, 0]},
	]:
		var before := animation.track_get_key_count(0) + animation.track_get_key_count(1)
		var refused: Dictionary = commands.execute("capability.set_animation_keyframe", base.merged(bad))
		_expect(refused.has("__error__"), "set_animation_keyframe accepted %s: %s" % [bad, refused])
		_expect(animation.track_get_key_count(0) + animation.track_get_key_count(1) == before, "a rejected keyframe %s changed the animation" % [bad])


func library_animation(animation: Animation) -> Animation:
	return animation


func _selector_script_path() -> void:
	var peer = RuntimePeer.new()
	var target := {"node_path": "/root/Main/Player", "node_type": "Node3D", "script_path": "res://scripts/player.gd", "script_sha256": "0".repeat(64), "property": "speed"}
	_expect(peer._selector_values_allowed("set-speed", target), "a valid script_path was rejected as a forbidden selector")
	var shell := target.duplicate()
	shell["property"] = "shell_command"
	_expect(not peer._selector_values_allowed("set-speed", shell), "another field with a forbidden term was accepted")
	var malformed := target.duplicate()
	malformed["script_path"] = "res://scripts/player.txt"
	_expect(not peer._selector_values_allowed("set-speed", malformed), "a script_path that is not a .gd path skipped the screen")
	_expect(not peer._selector_values_allowed("run-script", target), "a forbidden action id was accepted")
	peer.free()


func _resource_preview(commands) -> void:
	var first: Dictionary = commands.execute("capability.get_resource_preview", {"path": "res://icon.png"})
	_expect(not first.has("__error__") and first.has("available"), "get_resource_preview did not answer cleanly: %s" % [first])
	for attempt in 20:
		if first.get("available") == true: break
		await get_tree().create_timer(0.25).timeout
		first = commands.execute("capability.get_resource_preview", {"path": "res://icon.png"})
	if first.get("available") == true:
		_expect(FileAccess.file_exists(first.get("preview_path", "")), "the preview file was not written")
	else:
		_expect(not str(first.get("reason", "")).is_empty(), "an unavailable preview gave no reason: %s" % [first])
	print("PREVIEW_RESULT ", first)


func _export_path(commands) -> void:
	for bad in ["/tmp/game.pck", "../game.pck", ""]:
		_expect(commands.execute("capability.export_project", {"preset": "none", "path": bad}).has("__error__"), "export_project accepted the path %s" % bad)
	var result: Dictionary = commands.execute("capability.export_project", {"preset": "none", "path": "res://build/game.pck"})
	_expect(not result.has("__error__") and result.get("path") == "res://build/game.pck", "a res:// export path was rejected: %s" % [result])


func _project_file() -> String:
	return FileAccess.get_file_as_string("res://project.godot")


func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
		push_error(message)
		print("FAILED: ", message)
