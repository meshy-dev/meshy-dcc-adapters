extends SceneTree

const RuntimePeer = preload("res://addons/meshy_dcc_godot/runtime_peer.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	ProjectSettings.set_setting("meshy_dcc/playtest/project_id", "meshy-dcc-godot-ci")
	ProjectSettings.set_setting("meshy_dcc/playtest/session_id", "typed-action-smoke")
	ProjectSettings.set_setting("meshy_dcc/playtest/authority_id", "ci-playtest-owner")
	var peer = RuntimePeer.new()
	root.add_child(peer)
	await process_frame
	var status: Dictionary = peer._execute("get_runtime_status", {})
	var typed: Dictionary = status.get("typed_actions", {})
	if typed.get("available") == false and "manifest_path_reparse" in str(typed.get("reason", "")):
		print("TYPED_ACTION_LINK_REJECTED")
		quit(0)
	else:
		push_error("Typed action manifest reparse point was not rejected: %s" % status)
		quit(1)
