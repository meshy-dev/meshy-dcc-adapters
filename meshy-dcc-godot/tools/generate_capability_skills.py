"""Generate the declarative Godot capability skills from a compact catalog."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "meshy_dcc_godot" / "skills"

# Public capability vocabulary. Implementations are original and live in this package.
CATEGORIES = {
    "project-management": [
        ("get_project_info", "Return project metadata, version, viewport, and autoloads."),
        ("get_filesystem_tree", "Return a filtered recursive project file tree."),
        ("search_files", "Search project files by glob or name fragment."),
        ("get_project_settings", "Read project settings by prefix or key."),
        ("set_project_setting", "Set and persist one project setting."),
        ("uid_to_project_path", "Convert a Godot resource UID to res:// path."),
        ("project_path_to_uid", "Convert a res:// resource path to a Godot UID."),
    ],
    "scene-management": [
        ("get_scene_tree", "Return the edited scene hierarchy."),
        ("get_scene_file_content", "Read a bounded .tscn file as text."),
        ("create_scene", "Create and optionally open a new scene."),
        ("open_scene", "Open a scene in the editor."),
        ("delete_scene", "Delete a project scene file."),
        ("add_scene_instance", "Instance a PackedScene below an edited-scene node."),
        ("play_scene", "Run the main, current, or specified scene."),
        ("stop_scene", "Stop the running project."),
        ("save_scene", "Save the edited scene, optionally to a new path."),
    ],
    "node": [
        ("add_node", "Add a typed node with initial properties."),
        ("delete_node", "Delete a node with undo support."),
        ("duplicate_node", "Duplicate a node and its owned children."),
        ("move_node", "Reparent a node while preserving ownership."),
        (
            "update_property",
            "Set an existing node property, such as position, rotation, scale, transform or visible.",
        ),
        ("get_node_properties", "Return stored and editable node properties."),
        ("add_resource", "Create and assign a Resource to a node property."),
        ("set_anchor_preset", "Apply a Control anchor preset."),
        ("rename_node", "Rename an edited-scene node."),
        ("connect_signal", "Connect a signal between scene nodes."),
        ("disconnect_signal", "Disconnect a signal connection."),
        ("get_node_groups", "Return groups for a node."),
        ("set_node_groups", "Replace group membership for a node."),
        ("find_nodes_in_group", "Find edited-scene nodes in a group."),
    ],
    "script": [
        ("list_scripts", "List project GDScript files and global class metadata."),
        ("read_script", "Read a bounded project GDScript file."),
        ("create_script", "Create a GDScript file from source or a safe template."),
        ("edit_script", "Replace source or perform an exact search/replace edit."),
        ("attach_script", "Attach a project script to a scene node."),
        ("get_open_scripts", "List scripts currently open in the script editor."),
        ("validate_script", "Compile-check GDScript source or a project script."),
        ("search_in_files", "Search bounded text files under res://."),
    ],
    "editor": [
        ("get_editor_errors", "Return errors captured by the Meshy DCC editor plugin."),
        ("get_editor_screenshot", "Capture the selected editor viewport to a PNG."),
        (
            "get_game_screenshot",
            "Capture game pixels on the runtime thread and encode the PNG in the adapter.",
        ),
        (
            "execute_editor_script",
            "Run one @tool method with an observational budget and optional caller-driven chunks.",
        ),
        ("clear_output", "Clear errors captured by the Meshy DCC editor plugin."),
        ("get_signals", "Return node signals and their connections."),
        ("reload_plugin", "Reload the Meshy DCC editor plugin."),
        ("reload_project", "Rescan project files and reload changed scripts."),
        ("get_output_log", "Return recent Meshy DCC editor and runtime messages."),
    ],
    "input": [
        ("simulate_key", "Send a keyboard event to the running game."),
        ("simulate_mouse_click", "Send a mouse button event to the running game."),
        ("simulate_mouse_move", "Send mouse motion to the running game."),
        ("simulate_action", "Press or release a Godot input action in the running game."),
        ("simulate_sequence", "Queue a sequence of runtime input events."),
        ("get_input_actions", "List InputMap actions and deadzones."),
        ("set_input_action", "Create or replace an InputMap action."),
    ],
    "runtime": [
        ("get_runtime_status", "Return game-peer connection and play status."),
        (
            "execute_typed_action",
            "Execute one strict project-manifest action for bounded playtest control.",
        ),
        ("get_game_scene_tree", "Return one bounded page of the running game hierarchy."),
        ("get_game_node_properties", "Return one bounded property page from a game node."),
        ("set_game_node_property", "Set a property on a running-game node."),
        (
            "execute_game_script",
            "Compatibility-only broad public-method call; this is not an allowlist and is not a "
            "playtest or RL action path.",
        ),
        ("capture_frames", "Capture numbered runtime screenshots."),
        ("monitor_properties", "Sample runtime node properties over several frames."),
        ("start_recording", "Start recording injected input events."),
        ("stop_recording", "Stop recording and return recorded input events."),
        ("replay_recording", "Replay previously recorded input events."),
        ("find_nodes_by_script", "Find runtime nodes using a script path."),
        ("get_autoload", "Return a runtime autoload node snapshot."),
        ("batch_get_properties", "Read several runtime node properties."),
        ("find_ui_elements", "Find visible runtime Control nodes in one bounded traversal page."),
        ("click_button_by_text", "Activate a visible runtime button by text."),
        ("wait_for_node", "Check whether a runtime node exists."),
        ("find_nearby_nodes", "Find runtime 2D or 3D nodes near a position."),
        ("navigate_to", "Set a NavigationAgent target position."),
        ("move_to", "Move a runtime Node2D or Node3D toward a target."),
    ],
    "animation": [
        ("list_animations", "List AnimationPlayer libraries and animations."),
        ("create_animation", "Create an animation in an AnimationPlayer."),
        ("add_animation_track", "Add a typed animation track."),
        ("set_animation_keyframe", "Insert an animation key with optional easing."),
        ("get_animation_info", "Return animation tracks and keys."),
        ("remove_animation", "Remove an animation from a library."),
    ],
    "animation-tree": [
        ("create_animation_tree", "Create and configure an AnimationTree node."),
        ("get_animation_tree_structure", "Return AnimationTree parameters and tree type."),
        ("set_tree_parameter", "Set an AnimationTree parameter."),
        ("add_state_machine_state", "Add a state-machine animation node."),
        ("remove_state_machine_state", "Remove a state-machine node."),
        ("add_state_machine_transition", "Add a state-machine transition."),
        ("remove_state_machine_transition", "Remove a state-machine transition."),
        ("set_blend_tree_node", "Add or replace an AnimationNode in a blend tree."),
    ],
    "scene-3d": [
        ("add_mesh_instance", "Add a primitive MeshInstance3D."),
        ("setup_camera_3d", "Add or configure a Camera3D."),
        ("setup_lighting", "Add or configure a 3D light."),
        ("setup_environment", "Add or configure a WorldEnvironment."),
        ("add_gridmap", "Add and configure a GridMap."),
        ("set_material_3d", "Create or update a StandardMaterial3D override."),
    ],
    "physics": [
        ("setup_physics_body", "Configure physics-body properties."),
        ("setup_collision", "Add and configure a collision shape."),
        ("set_physics_layers", "Set collision layer and mask."),
        ("get_physics_layers", "Read collision layer and mask."),
        ("get_collision_info", "Return collision child and shape details."),
        ("add_raycast", "Add a RayCast2D or RayCast3D."),
    ],
    "particle": [
        ("create_particles", "Add GPUParticles2D or GPUParticles3D."),
        ("set_particle_material", "Configure a ParticleProcessMaterial."),
        ("set_particle_color_gradient", "Set particle color gradient points."),
        ("apply_particle_preset", "Apply a deterministic particle preset."),
        ("get_particle_info", "Return particle system properties."),
    ],
    "navigation": [
        ("setup_navigation_region", "Add or configure a navigation region."),
        ("setup_navigation_agent", "Add or configure a navigation agent."),
        ("bake_navigation_mesh", "Bake a NavigationMesh in the editor."),
        ("set_navigation_layers", "Set navigation layers on a node."),
        ("get_navigation_info", "Return navigation node configuration."),
        ("query_navigation_path", "Query a 2D or 3D navigation path."),
    ],
    "audio": [
        ("add_audio_player", "Add an audio stream player node."),
        ("add_audio_bus", "Add an audio bus."),
        ("add_audio_bus_effect", "Add an AudioEffect to a bus."),
        ("set_audio_bus", "Configure volume, mute, solo, or bypass."),
        ("get_audio_bus_layout", "Return buses and effects."),
        ("get_audio_info", "Return audio-node configuration."),
    ],
    "tilemap": [
        ("tilemap_set_cell", "Set one TileMapLayer cell."),
        ("tilemap_fill_rect", "Fill a rectangle of TileMapLayer cells."),
        ("tilemap_get_cell", "Read one TileMapLayer cell."),
        ("tilemap_clear", "Clear TileMapLayer cells."),
        ("tilemap_get_info", "Return TileMapLayer and TileSet information."),
        ("tilemap_get_used_cells", "Return used TileMapLayer coordinates."),
    ],
    "theme-ui": [
        ("create_theme", "Create and save a Theme resource."),
        ("set_theme_color", "Set a Theme color item."),
        ("set_theme_constant", "Set a Theme constant item."),
        ("set_theme_font_size", "Set a Theme font-size item."),
        ("set_theme_stylebox", "Create and set a StyleBoxFlat item."),
        ("get_theme_info", "Return Theme item lists for a type."),
    ],
    "shader": [
        ("create_shader", "Create a bounded .gdshader resource."),
        ("read_shader", "Read a project shader file."),
        ("edit_shader", "Replace or search/replace shader source."),
        (
            "assign_shader_material",
            "Assign a ShaderMaterial to a CanvasItem or GeometryInstance3D.",
        ),
        ("set_shader_param", "Set one ShaderMaterial parameter."),
        ("get_shader_params", "Return shader parameters on a node material."),
    ],
    "resource": [
        ("read_resource", "Load and serialize a resource property summary."),
        ("edit_resource", "Set properties and save a project resource."),
        ("create_resource", "Instantiate and save a typed Resource."),
        ("get_resource_preview", "Generate or return a cached resource preview."),
        ("add_autoload", "Register a project autoload singleton."),
        ("remove_autoload", "Remove a project autoload singleton."),
    ],
    "batch-refactor": [
        ("find_nodes_by_type", "Find edited-scene nodes by class."),
        ("find_signal_connections", "Return scene signal connections."),
        ("batch_set_property", "Set a property on matching edited-scene nodes."),
        ("find_node_references", "Search project text for a node path or name."),
        ("get_scene_dependencies", "Return dependencies for a scene resource."),
        ("cross_scene_set_property", "Update matching nodes across project scenes."),
        ("find_script_references", "Find project references to a script or resource."),
        ("detect_circular_dependencies", "Detect circular PackedScene dependencies."),
    ],
    "analysis": [
        ("analyze_scene_complexity", "Count nodes and high-cost scene features."),
        ("analyze_signal_flow", "Map edited-scene signal flow."),
        ("find_unused_resources", "Find project resources with no text references."),
        ("get_project_statistics", "Return project file, scene, script, and resource counts."),
    ],
    "testing-qa": [
        ("run_test_scenario", "Run a sequence of runtime actions and assertions."),
        ("assert_node_state", "Assert runtime node existence and properties."),
        ("assert_screen_text", "Assert visible runtime text."),
        ("compare_screenshots", "Compare two PNGs using bounded pixel sampling."),
        ("run_stress_test", "Sample runtime performance for a bounded frame count."),
        ("get_test_report", "Return the latest runtime test report."),
    ],
    "profiling": [
        ("get_performance_monitors", "Return runtime Performance monitor values."),
        ("get_editor_performance", "Return editor process memory and frame summary."),
    ],
    "export": [
        ("list_export_presets", "List project export presets without secrets."),
        ("export_project", "Export a project using a named preset and safe project path."),
        ("get_export_info", "Return export configuration and template availability."),
    ],
}

READ_ONLY_PREFIXES = (
    "get_",
    "list_",
    "read_",
    "search_",
    "find_",
    "analyze_",
    "assert_",
    "compare_",
    "detect_",
    "uid_",
    "project_path_",
    "wait_",
)

DESTRUCTIVE = {
    "delete_scene",
    "delete_node",
    "edit_script",
    "execute_editor_script",
    "execute_game_script",
    "execute_typed_action",
    "cross_scene_set_property",
    "edit_shader",
    "edit_resource",
    "remove_autoload",
    "export_project",
}

STRING = {"type": "string", "maxLength": 500}
PATH = {"type": "string", "pattern": "^res://", "maxLength": 500}
NODE_PATH = {"type": "string", "maxLength": 500}
PROPERTIES = {"type": "object"}
VALUE = {}
VECTOR = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 4}

IDENTITY = {
    "type": "string",
    "minLength": 1,
    "maxLength": 128,
    "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]*$",
}
DIGEST = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
INPUT_ACTION_TARGET = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action"],
    "properties": {"action": IDENTITY},
}
PROPERTY_TARGET = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "node_path",
        "node_type",
        "script_path",
        "script_sha256",
        "property",
    ],
    "properties": {
        "node_path": {
            "type": "string",
            "pattern": "^/root/[A-Za-z0-9_./:-]+$",
            "maxLength": 500,
        },
        "node_type": IDENTITY,
        "script_path": {
            "type": "string",
            "pattern": "^res://[A-Za-z0-9_./-]+[.]gd$",
            "maxLength": 500,
        },
        "script_sha256": DIGEST,
        "property": IDENTITY,
    },
}
INPUT_ACTION_REQUEST = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "kind", "target", "arguments"],
    "properties": {
        "id": IDENTITY,
        "kind": {"const": "input_action"},
        "target": INPUT_ACTION_TARGET,
        "arguments": {
            "type": "object",
            "additionalProperties": False,
            "required": ["pressed", "strength"],
            "properties": {
                "pressed": {"type": "boolean"},
                "strength": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
        },
    },
}
PROPERTY_REQUEST = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "kind", "target", "arguments"],
    "properties": {
        "id": IDENTITY,
        "kind": {"const": "set_property"},
        "target": PROPERTY_TARGET,
        "arguments": {
            "type": "object",
            "additionalProperties": False,
            "required": ["value"],
            "properties": {"value": {"type": ["boolean", "integer", "number", "string"]}},
        },
    },
}
TYPED_ACTION_INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "project_id",
        "session_id",
        "runtime_id",
        "authority_id",
        "manifest_id",
        "manifest_digest",
        "action",
    ],
    "properties": {
        "project_id": IDENTITY,
        "session_id": IDENTITY,
        "runtime_id": IDENTITY,
        "authority_id": IDENTITY,
        "manifest_id": IDENTITY,
        "manifest_digest": DIGEST,
        "action": {"oneOf": [INPUT_ACTION_REQUEST, PROPERTY_REQUEST]},
    },
}
COMPATIBILITY_METHOD_INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["node_path", "method", "arguments"],
    "properties": {
        "node_path": NODE_PATH,
        "method": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_]{0,127}$",
        },
        "arguments": {"type": "array", "maxItems": 8},
    },
}
TYPED_ACTION_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "schema_version",
        "manifest_id",
        "manifest_digest",
        "action_id",
        "kind",
        "target",
        "readback",
        "budget",
    ],
    "properties": {
        "status": {"const": "applied"},
        "schema_version": {"const": 1},
        "manifest_id": IDENTITY,
        "manifest_digest": DIGEST,
        "action_id": IDENTITY,
        "kind": {"enum": ["input_action", "set_property"]},
        "target": {"oneOf": [INPUT_ACTION_TARGET, PROPERTY_TARGET]},
        "readback": {
            "oneOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["kind", "action", "pressed", "strength"],
                    "properties": {
                        "kind": {"const": "input_action"},
                        "action": IDENTITY,
                        "pressed": {"type": "boolean"},
                        "strength": {"type": "number"},
                    },
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "kind",
                        "node_path",
                        "node_type",
                        "property",
                        "value",
                        "script_sha256",
                    ],
                    "properties": {
                        "kind": {"const": "property"},
                        "node_path": {"type": "string"},
                        "node_type": IDENTITY,
                        "property": IDENTITY,
                        "value": {"type": ["boolean", "integer", "number", "string"]},
                        "script_sha256": DIGEST,
                    },
                },
            ]
        },
        "budget": {
            "type": "object",
            "additionalProperties": False,
            "required": ["used", "remaining", "limit"],
            "properties": {
                "used": {"type": "integer", "minimum": 1},
                "remaining": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1},
            },
        },
    },
}

# get_runtime_status and get_game_node_properties still take this shared schema:
# test_main_thread_budget_contract pins max_nodes in their blocks, though neither
# handler reads it. Every other tool declares its own in TOOL_INPUT_SCHEMAS.
CATEGORY_PROPERTIES = {
    "runtime": {
        "node_path": NODE_PATH,
        "path": PATH,
        "property": STRING,
        "properties": {"type": "array", "items": STRING},
        "value": VALUE,
        "method": STRING,
        "arguments": {"type": "array", "maxItems": 8},
        "targets": {"type": "array", "items": {"type": "object"}, "maxItems": 500},
        "events": {"type": "array", "items": {"type": "object"}, "maxItems": 100},
        "steps": {"type": "array", "items": {"type": "object"}, "maxItems": 100},
        "text": STRING,
        "target": VECTOR,
        "radius": {"type": "number", "minimum": 0},
        "equals": PROPERTIES,
        "cursor": STRING,
        "budget_ms": {"type": "integer", "minimum": 1, "maximum": 50},
        "start_index": {"type": "integer", "minimum": 0, "maximum": 10000},
        "max_nodes": {"type": "integer", "minimum": 1, "maximum": 128},
        "max_properties": {"type": "integer", "minimum": 1, "maximum": 128},
    },
}

SCRIPT = """from meshy_dcc_core.skill import skill_entry

from meshy_dcc_godot.capability_dispatch import dispatch


@skill_entry
def main(_action_name: str = "", **params):
    return dispatch(_action_name, params)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
"""

# These handlers only wait on the Godot websocket. The plugin still performs
# the bounded host operation on Godot's own runtime thread.
REMOTE_BRIDGE_ANY_AFFINITY = {
    ("runtime", "find_ui_elements"),
    ("runtime", "get_game_node_properties"),
    ("runtime", "get_game_scene_tree"),
    ("runtime", "get_runtime_status"),
}


# Words agents search with that a tool's description does not contain. Godot has no
# separate transform tool; update_property sets position, rotation, scale and visible.
TOOL_SEARCH_ALIASES = {
    "update_property": [
        "move node",
        "rotate node",
        "scale node",
        "hide node",
        "show node",
        "set position",
        "set rotation",
        "set transform",
    ],
}


# Tools whose parameters are spelled out, matching what the editor
# (capabilities.gd) or the running game (runtime_peer.gd) reads for them.
SCENE_NODE = dict(NODE_PATH, description="Edited-scene node path; empty or '.' is the scene root.")
RUNTIME_NODE = dict(
    NODE_PATH,
    description="Running-game node path such as /root/Main/Player; "
    "empty or '.' is the current scene.",
)
SOURCE = {"type": "string", "maxLength": 1000000}
TRUE = {"type": "boolean", "default": True}
FALSE = {"type": "boolean", "default": False}
NAMES = {"type": "array", "items": STRING}
POINT = dict(VECTOR, maxItems=2)
POINT_OR_3D = dict(VECTOR, maxItems=3)
CELL = {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}
# Kept bare: test_main_thread_budget_contract pins these exact strings in the
# schemas of the budgeted polling reads.
BUDGET_MS = {"type": "integer", "minimum": 1, "maximum": 50}
PAGE_SIZE = {"type": "integer", "minimum": 1, "maximum": 128}
CURSOR = dict(
    STRING, description="next_cursor from the previous page; empty starts at the beginning."
)
UI_PAGE = {
    "cursor": CURSOR,
    "max_nodes": dict(PAGE_SIZE, default=64),
    "budget_ms": dict(BUDGET_MS, default=40),
}
INITIAL = dict(PROPERTIES, description="Initial values for existing properties.")
EVENTS = {
    "type": "array",
    "items": {"type": "object"},
    "maxItems": 100,
    "description": "Each event is {type: key, mouse_click, mouse_move or action (default), "
    "plus that simulate tool's parameters}.",
}
SEARCH = {
    "query": dict(STRING, description="Case-insensitive text to find."),
    "extensions": dict(
        NAMES,
        description="Extensions to search, without the dot; "
        "default gd, tscn, tres, gdshader, cfg, json.",
    ),
}
ANIMATION_PLAYER = dict(
    SCENE_NODE, description="An AnimationPlayer; empty or '.' is the scene root."
)
ANIMATION = dict(STRING, description="Animation name; library/name outside the default library.")
ANIMATION_TREE = dict(SCENE_NODE, description="An AnimationTree; empty or '.' is the scene root.")
PARTICLES = dict(
    SCENE_NODE, description="A GPUParticles2D or GPUParticles3D; empty or '.' is the scene root."
)
TILEMAP_LAYER = dict(SCENE_NODE, description="A TileMapLayer; empty or '.' is the scene root.")
TILE = {
    "source_id": {
        "type": "integer",
        "minimum": -1,
        "description": "TileSet source id; -1 erases the cell.",
    },
    "atlas_coords": dict(CELL, description="Tile [x, y] in the atlas source."),
    "alternative": {"type": "integer", "minimum": 0, "default": 0},
}
THEME = dict(PATH, description="An existing Theme .tres or .res file.")
THEME_TYPE = dict(STRING, default="Control", description="Theme type, such as Button.")
THEME_ITEM = dict(STRING, description="Theme item name, such as font_color.")
SHADER_NODE = dict(
    SCENE_NODE, description="A node with a ShaderMaterial; empty or '.' is the scene root."
)
NODE_TYPE = dict(
    STRING, default="Node", description="Godot class; subclasses match, so Node matches every node."
)


def _object(properties: dict, *required: str) -> dict:
    schema = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = list(required)
    return schema


def _child(default_name: str) -> dict:
    """Name and parent of a node a tool adds to the edited scene."""
    return {
        "name": dict(STRING, description=f"Node name, default {default_name}."),
        "parent_path": dict(SCENE_NODE, description="Parent node path, default the scene root."),
    }


def _text_edit(path_description: str) -> dict:
    return {
        "path": dict(PATH, description=path_description),
        "source": dict(SOURCE, description="Full replacement text."),
        "search": {
            "type": "string",
            "maxLength": 100000,
            "description": "Exact text to replace when source is not given.",
        },
        "replace": {"type": "string", "maxLength": 100000, "default": ""},
        "replace_all": dict(
            FALSE, description="Replace every match; otherwise search must be unique."
        ),
        "allow_empty": dict(FALSE, description="Allow the result to be empty."),
    }


def _configured_child(kind: str, default_name: str) -> dict:
    """setup_* tools that configure an existing node or add one when the path is not found."""
    return {
        "node_path": dict(
            SCENE_NODE,
            description=f"{kind} to configure; a path that is not found adds a new one. "
            "Empty is the scene root.",
        ),
        **_child(default_name),
    }


TOOL_INPUT_SCHEMAS = {
    # project-management
    "get_project_info": _object({}),
    "get_filesystem_tree": _object(
        {
            "extensions": dict(
                NAMES, description="Extensions to include, without the dot; default all."
            )
        }
    ),
    "search_files": _object(
        {
            "query": dict(
                STRING, description="Case-insensitive part of the res:// path; empty matches all."
            ),
            "extension": dict(
                STRING, description="Only files with this extension, without the dot."
            ),
        }
    ),
    "get_project_settings": _object(
        {
            "prefix": dict(
                STRING, description="Setting name or prefix; empty returns all, up to 500."
            ),
            "key": dict(STRING, description="Same as prefix, read when prefix is absent."),
        }
    ),
    "set_project_setting": _object(
        {
            "key": dict(STRING, description="Setting name; autoload/ keys are refused."),
            "value": VALUE,
        },
        "key",
        "value",
    ),
    "uid_to_project_path": _object(
        {"uid": dict(STRING, description="uid://... text, or the numeric id as a string.")}, "uid"
    ),
    "project_path_to_uid": _object({"path": PATH}, "path"),
    # scene-management
    "get_scene_tree": _object({}),
    "get_scene_file_content": _object(
        {"path": dict(PATH, description="An existing .tscn file.")}, "path"
    ),
    "create_scene": _object(
        {
            "path": dict(PATH, description="New .tscn file."),
            "root_type": dict(
                STRING, default="Node2D", description="Godot Node class of the root."
            ),
            "root_name": dict(STRING, default="Root"),
            "open": dict(TRUE, description="Open the scene in the editor."),
            "overwrite": dict(FALSE, description="Replace an existing file."),
        },
        "path",
    ),
    "open_scene": _object({"path": dict(PATH, description="An existing .tscn file.")}, "path"),
    "delete_scene": _object(
        {"path": dict(PATH, description="An existing .tscn file that is not the edited scene.")},
        "path",
    ),
    "add_scene_instance": _object(
        {
            "scene_path": dict(PATH, description="An existing .tscn, .scn, .glb or .gltf file."),
            **_child("the scene root's name"),
        },
        "scene_path",
    ),
    "play_scene": _object(
        {
            "mode": {"type": "string", "enum": ["main", "current", "custom"], "default": "current"},
            "path": dict(PATH, description="The .tscn or .scn to run when mode is custom."),
        }
    ),
    "stop_scene": _object({}),
    "save_scene": _object(
        {"path": dict(PATH, description="Save as this .tscn; default the scene's own file.")}
    ),
    # node
    "add_node": _object(
        {
            "type": dict(STRING, description="Godot Node class, default Node2D."),
            "name": dict(STRING, description="Node name, default the class name."),
            "parent_path": dict(
                SCENE_NODE, description="Parent node path, default the scene root."
            ),
            "properties": dict(PROPERTIES, description="Initial values for existing properties."),
        }
    ),
    "delete_node": _object(
        {"node_path": dict(NODE_PATH, description="A non-root edited-scene node.")}, "node_path"
    ),
    "duplicate_node": _object(
        {
            "node_path": NODE_PATH,
            "name": dict(STRING, description="Name of the copy, default <name>Copy."),
            "parent_path": dict(
                NODE_PATH, description="Parent of the copy, default the original's parent."
            ),
        },
        "node_path",
    ),
    "move_node": _object(
        {
            "node_path": NODE_PATH,
            "parent_path": dict(
                NODE_PATH, description="New parent; must not be the node or below it."
            ),
            "keep_global_transform": {"type": "boolean", "default": True},
        },
        "node_path",
        "parent_path",
    ),
    "update_property": _object(
        {"node_path": SCENE_NODE, "property": STRING, "value": VALUE}, "property", "value"
    ),
    "get_node_properties": _object({"node_path": SCENE_NODE}),
    "add_resource": _object(
        {
            "node_path": SCENE_NODE,
            "property": dict(
                STRING, description="Existing node property that receives the resource."
            ),
            "resource_type": dict(STRING, description="Godot Resource class, default Resource."),
            "properties": dict(
                PROPERTIES, description="Initial values for the resource's properties."
            ),
        },
        "property",
    ),
    "set_anchor_preset": _object(
        {
            "node_path": dict(SCENE_NODE, description="A Control node."),
            "preset": {
                "type": "integer",
                "minimum": 0,
                "maximum": 15,
                "default": 15,
                "description": "Control.LayoutPreset value; 15 is PRESET_FULL_RECT.",
            },
            "keep_offsets": {"type": "boolean", "default": False},
        }
    ),
    "rename_node": _object(
        {"node_path": NODE_PATH, "name": dict(STRING, description="New name, without '/'.")},
        "node_path",
        "name",
    ),
    "connect_signal": _object(
        {
            "source_path": NODE_PATH,
            "signal": STRING,
            "target_path": NODE_PATH,
            "method": STRING,
            "flags": {
                "type": "integer",
                "minimum": 0,
                "default": 0,
                "description": "Object.ConnectFlags bits.",
            },
        },
        "source_path",
        "signal",
        "target_path",
        "method",
    ),
    "disconnect_signal": _object(
        {"source_path": NODE_PATH, "signal": STRING, "target_path": NODE_PATH, "method": STRING},
        "source_path",
        "signal",
        "target_path",
        "method",
    ),
    "get_node_groups": _object({"node_path": SCENE_NODE}),
    "set_node_groups": _object(
        {
            "node_path": SCENE_NODE,
            "groups": {
                "type": "array",
                "items": STRING,
                "description": "The node's complete group list.",
            },
        },
        "groups",
    ),
    "find_nodes_in_group": _object({"group": STRING}, "group"),
    # script
    "list_scripts": _object({}),
    "read_script": _object({"path": dict(PATH, description="An existing .gd file.")}, "path"),
    "create_script": _object(
        {
            "path": dict(PATH, description="New .gd file."),
            "source": dict(SOURCE, description="Script text, default 'extends <base_type>'."),
            "base_type": dict(
                STRING, default="Node", description="Class to extend when source is not given."
            ),
            "overwrite": dict(FALSE, description="Replace an existing file."),
        },
        "path",
    ),
    "edit_script": _object(_text_edit("An existing .gd file."), "path"),
    "attach_script": _object(
        {"node_path": SCENE_NODE, "script_path": dict(PATH, description="An existing .gd file.")},
        "script_path",
    ),
    "get_open_scripts": _object({}),
    "validate_script": _object(
        {
            "source": dict(
                SOURCE, description="GDScript to compile; when empty, path is read instead."
            ),
            "path": dict(
                PATH, description="An existing .gd file, checked when source is not given."
            ),
        }
    ),
    "search_in_files": _object(SEARCH, "query"),
    # editor
    "get_editor_errors": _object({}),
    "get_editor_screenshot": _object(
        {
            "path": dict(
                PATH, default="res://.meshy-dcc/editor.png", description="Output .png file."
            ),
            "mode": {"type": "string", "enum": ["2d", "3d"], "default": "3d"},
            "viewport": {
                "type": "integer",
                "minimum": 0,
                "maximum": 3,
                "default": 0,
                "description": "3D editor viewport index.",
            },
            "budget_ms": BUDGET_MS,
            "include_base64": dict(FALSE, description="Also return the PNG as base64."),
        }
    ),
    "get_game_screenshot": _object(
        {
            "path": dict(
                PATH, default="res://.meshy-dcc/game.png", description="Output .png file."
            ),
            "include_base64": dict(FALSE, description="Also return the PNG as base64."),
        }
    ),
    "execute_editor_script": _object(
        {
            "path": dict(PATH, description="An existing @tool .gd file."),
            "method": dict(
                STRING,
                default="run",
                description="Method to call with arguments as its one argument.",
            ),
            "arguments": dict(VALUE, default={}, description="Value passed to the method."),
            "budget_ms": dict(
                BUDGET_MS,
                default=50,
                description="Compared with the elapsed time; the call is not preempted.",
            ),
            "chunked": dict(
                FALSE,
                description="The method returns {done, next_cursor}; "
                "the reply carries the next call.",
            ),
        },
        "path",
    ),
    "clear_output": _object({}),
    "get_signals": _object({"node_path": SCENE_NODE}),
    "reload_plugin": _object({}),
    "reload_project": _object({}),
    "get_output_log": _object({}),
    # input
    "simulate_key": _object(
        {
            "keycode": {
                "type": "integer",
                "default": 0,
                "description": "Godot Key code, such as 65 for A.",
            },
            "physical_keycode": {"type": "integer", "default": 0},
            "pressed": TRUE,
            "echo": FALSE,
        }
    ),
    "simulate_mouse_click": _object(
        {
            "position": dict(POINT, description="Viewport [x, y], default [0, 0]."),
            "button": {
                "type": "integer",
                "default": 1,
                "description": "MouseButton: 1 left, 2 right, 3 middle.",
            },
            "pressed": TRUE,
        }
    ),
    "simulate_mouse_move": _object(
        {
            "position": dict(POINT, description="Viewport [x, y], default [0, 0]."),
            "relative": dict(POINT, description="Motion [dx, dy], default [0, 0]."),
        }
    ),
    "simulate_action": _object(
        {
            "action": dict(STRING, description="An existing InputMap action."),
            "pressed": TRUE,
            "strength": {"type": "number", "default": 1.0, "description": "Press strength."},
        },
        "action",
    ),
    "simulate_sequence": _object({"events": EVENTS}, "events"),
    "get_input_actions": _object({}),
    "set_input_action": _object(
        {
            "action": dict(STRING, description="Action name; created when missing."),
            "deadzone": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Default 0.5 for a new action, otherwise unchanged.",
            },
            "replace_events": dict(FALSE, description="Remove the action's existing events first."),
            "keycode": {
                "type": "integer",
                "description": "Add a key event with this Godot Key code.",
            },
        },
        "action",
    ),
    # runtime; get_runtime_status and get_game_node_properties keep the shared
    # runtime schema (see CATEGORY_PROPERTIES).
    "get_game_scene_tree": _object(
        {"cursor": CURSOR, "max_nodes": PAGE_SIZE, "budget_ms": BUDGET_MS}
    ),
    "set_game_node_property": _object(
        {"node_path": RUNTIME_NODE, "property": STRING, "value": VALUE}, "property", "value"
    ),
    "capture_frames": _object(
        {
            "count": {"type": "integer", "minimum": 1, "maximum": 10, "default": 1},
            "path": dict(
                PATH,
                default="res://.meshy-dcc/frames/frame",
                description="Base path; frames are written as <path>_000.png and on.",
            ),
            "start_index": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10000,
                "default": 0,
                "description": "First frame number; resume with next_index.",
            },
            "budget_ms": dict(BUDGET_MS, default=40),
        }
    ),
    "monitor_properties": _object(
        {
            "targets": {
                "type": "array",
                "items": _object({"node_path": RUNTIME_NODE, "property": STRING}, "property"),
                "maxItems": 500,
            }
        },
        "targets",
    ),
    "start_recording": _object({}),
    "stop_recording": _object({}),
    "replay_recording": _object(
        {
            "events": dict(
                EVENTS, description="Events from stop_recording; default the last recording."
            )
        }
    ),
    "find_nodes_by_script": _object(
        {"script_path": dict(PATH, description="Script resource path of the nodes to find.")},
        "script_path",
    ),
    "get_autoload": _object(
        {"name": dict(STRING, description="Autoload name below /root.")}, "name"
    ),
    "batch_get_properties": _object(
        {
            "targets": {
                "type": "array",
                "items": _object(
                    {
                        "node_path": RUNTIME_NODE,
                        "properties": dict(
                            NAMES, description="Property names; default every stored property."
                        ),
                        "cursor": CURSOR,
                        "max_properties": dict(PAGE_SIZE, default=64),
                        "budget_ms": dict(BUDGET_MS, default=40),
                    }
                ),
                "maxItems": 500,
                "description": "One property page request per node.",
            }
        },
        "targets",
    ),
    "find_ui_elements": _object(
        {
            "text": dict(
                STRING,
                description="Case-insensitive text filter; empty lists every visible Control.",
            ),
            "cursor": CURSOR,
            "max_nodes": PAGE_SIZE,
            "budget_ms": BUDGET_MS,
        }
    ),
    "click_button_by_text": _object(
        {"text": dict(STRING, description="Exact text of a visible, enabled button."), **UI_PAGE},
        "text",
    ),
    "wait_for_node": _object({"node_path": RUNTIME_NODE}),
    "find_nearby_nodes": _object(
        {
            "node_path": dict(
                RUNTIME_NODE,
                description="Origin Node2D or Node3D; empty or '.' is the current scene.",
            ),
            "radius": {"type": "number", "minimum": 0, "default": 100},
        }
    ),
    "navigate_to": _object(
        {
            "node_path": dict(
                RUNTIME_NODE, description="A NavigationAgent2D or NavigationAgent3D."
            ),
            "target": dict(POINT_OR_3D, description="[x, y] or [x, y, z], default the origin."),
        }
    ),
    "move_to": _object(
        {
            "node_path": dict(
                RUNTIME_NODE, description="A Node2D or Node3D; empty or '.' is the current scene."
            ),
            "target": dict(POINT_OR_3D, description="[x, y] or [x, y, z], default the origin."),
            "amount": {
                "type": "number",
                "minimum": 0,
                "description": "Distance to move in this call, default speed times one frame.",
            },
            "speed": {
                "type": "number",
                "default": 100,
                "description": "Units per second, used without amount.",
            },
        }
    ),
    # animation
    "list_animations": _object({"node_path": ANIMATION_PLAYER}),
    "create_animation": _object(
        {
            "node_path": ANIMATION_PLAYER,
            "animation": dict(STRING, description="New animation name."),
            "library": dict(
                STRING,
                default="",
                description="Library, created when missing; empty is the default.",
            ),
            "length": {
                "type": "number",
                "exclusiveMinimum": 0,
                "default": 1.0,
                "description": "Seconds.",
            },
            "loop_mode": {
                "type": "integer",
                "minimum": 0,
                "maximum": 2,
                "default": 0,
                "description": "Animation.LoopMode: 0 none, 1 linear, 2 ping-pong.",
            },
            "overwrite": dict(FALSE, description="Replace an existing animation."),
        },
        "animation",
    ),
    "add_animation_track": _object(
        {
            "node_path": ANIMATION_PLAYER,
            "animation": ANIMATION,
            "track_type": {
                "type": "string",
                "enum": [
                    "value",
                    "position_3d",
                    "rotation_3d",
                    "scale_3d",
                    "method",
                    "bezier",
                    "audio",
                    "animation",
                ],
                "default": "value",
            },
            "property_path": dict(
                NODE_PATH,
                description="Track path from the player's root node, such as Sprite2D:position.",
            ),
            "interpolation": {
                "type": "integer",
                "minimum": 0,
                "maximum": 4,
                "default": 1,
                "description": "Animation.InterpolationType: 0 nearest, 1 linear, 2 cubic, "
                "3 linear angle, 4 cubic angle.",
            },
        },
        "animation",
        "property_path",
    ),
    "set_animation_keyframe": _object(
        {
            "node_path": ANIMATION_PLAYER,
            "animation": ANIMATION,
            "track": {
                "type": "integer",
                "minimum": 0,
                "description": "Track index from add_animation_track.",
            },
            "time": {"type": "number", "minimum": 0, "default": 0},
            "value": VALUE,
            "transition": {"type": "number", "default": 1.0, "description": "Easing; 1 is linear."},
        },
        "animation",
        "track",
        "value",
    ),
    "get_animation_info": _object(
        {"node_path": ANIMATION_PLAYER, "animation": ANIMATION}, "animation"
    ),
    "remove_animation": _object(
        {
            "node_path": ANIMATION_PLAYER,
            "animation": dict(STRING, description="Animation name within library."),
            "library": dict(STRING, default="", description="Empty is the default library."),
        },
        "animation",
    ),
    # animation-tree
    "create_animation_tree": _object(
        {
            **_child("AnimationTree"),
            "tree_type": {
                "type": "string",
                "enum": ["state_machine", "blend_tree"],
                "default": "state_machine",
            },
            "active": TRUE,
        }
    ),
    "get_animation_tree_structure": _object({"node_path": ANIMATION_TREE}),
    "set_tree_parameter": _object(
        {
            "node_path": ANIMATION_TREE,
            "parameter": dict(
                STRING, description="Parameter path; the parameters/ prefix is optional."
            ),
            "value": VALUE,
        },
        "parameter",
        "value",
    ),
    "add_state_machine_state": _object(
        {
            "node_path": ANIMATION_TREE,
            "state": dict(STRING, description="New state name."),
            "animation": dict(STRING, description="Animation to play, default the state name."),
            "position": dict(POINT, description="Graph position, default [0, 0]."),
        },
        "state",
    ),
    "remove_state_machine_state": _object({"node_path": ANIMATION_TREE, "state": STRING}, "state"),
    "add_state_machine_transition": _object(
        {
            "node_path": ANIMATION_TREE,
            "from": STRING,
            "to": STRING,
            "xfade_time": {"type": "number", "minimum": 0, "default": 0},
            "advance_mode": {
                "type": "integer",
                "minimum": 0,
                "maximum": 2,
                "default": 1,
                "description": "0 disabled, 1 enabled, 2 auto.",
            },
        },
        "from",
        "to",
    ),
    "remove_state_machine_transition": _object(
        {"node_path": ANIMATION_TREE, "from": STRING, "to": STRING}, "from", "to"
    ),
    "set_blend_tree_node": _object(
        {
            "node_path": ANIMATION_TREE,
            "name": dict(
                STRING,
                default="Node",
                description="Blend-tree node name; an existing one is replaced.",
            ),
            "type": dict(
                STRING, default="AnimationNodeAnimation", description="AnimationNode class."
            ),
            "position": dict(POINT, description="Graph position, default [0, 0]."),
        }
    ),
    # scene-3d
    "add_mesh_instance": _object(
        {
            "primitive": {
                "type": "string",
                "enum": ["box", "sphere", "capsule", "cylinder", "plane", "quad", "prism", "torus"],
                "default": "box",
            },
            **_child("Mesh"),
            "mesh_properties": dict(
                PROPERTIES, description="Initial values for the mesh's properties."
            ),
        }
    ),
    "setup_camera_3d": _object(
        {
            **_configured_child("Camera3D", "Camera3D"),
            "properties": dict(PROPERTIES, description="Camera3D property values."),
        }
    ),
    "setup_lighting": _object(
        {
            "light_type": {
                "type": "string",
                "enum": ["directional", "omni", "spot"],
                "default": "directional",
            },
            **_child("the light class"),
            "properties": dict(PROPERTIES, description="Light property values."),
        }
    ),
    "setup_environment": _object(
        {
            **_configured_child("WorldEnvironment", "WorldEnvironment"),
            "properties": dict(PROPERTIES, description="Environment resource property values."),
        }
    ),
    "add_gridmap": _object({**_child("GridMap"), "properties": INITIAL}),
    "set_material_3d": _object(
        {
            "node_path": dict(
                SCENE_NODE, description="A GeometryInstance3D; empty or '.' is the scene root."
            ),
            "properties": dict(PROPERTIES, description="StandardMaterial3D property values."),
        }
    ),
    # physics
    "setup_physics_body": _object(
        {
            "node_path": SCENE_NODE,
            "properties": dict(PROPERTIES, description="Property values for the node."),
        }
    ),
    "setup_collision": _object(
        {
            "is_3d": TRUE,
            "shape": {"type": "string", "enum": ["box", "circle", "capsule"], "default": "box"},
            "shape_properties": dict(
                PROPERTIES, description="Initial values for the shape's properties."
            ),
            **_child("CollisionShape3D or CollisionShape2D"),
        }
    ),
    "set_physics_layers": _object(
        {
            "node_path": SCENE_NODE,
            "layer": {
                "type": "integer",
                "minimum": 0,
                "description": "collision_layer bits, default unchanged.",
            },
            "mask": {
                "type": "integer",
                "minimum": 0,
                "description": "collision_mask bits, default unchanged.",
            },
        }
    ),
    "get_physics_layers": _object({"node_path": SCENE_NODE}),
    "get_collision_info": _object({"node_path": SCENE_NODE}),
    "add_raycast": _object({"is_3d": TRUE, **_child("RayCast"), "properties": INITIAL}),
    # particle
    "create_particles": _object({"is_3d": FALSE, **_child("Particles"), "properties": INITIAL}),
    "set_particle_material": _object(
        {
            "node_path": PARTICLES,
            "properties": dict(PROPERTIES, description="ParticleProcessMaterial property values."),
        }
    ),
    "set_particle_color_gradient": _object(
        {
            "node_path": PARTICLES,
            "colors": {
                "type": "array",
                "items": STRING,
                "minItems": 2,
                "default": ["#ffffffff", "#ffffff00"],
                "description": "Color strings such as #ff8800ff, one per offset.",
            },
            "offsets": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "default": [0.0, 1.0],
                "description": "Gradient positions from 0 to 1.",
            },
        }
    ),
    "apply_particle_preset": _object(
        {
            "node_path": PARTICLES,
            "preset": {"type": "string", "enum": ["fire", "smoke", "sparks"], "default": "fire"},
        }
    ),
    "get_particle_info": _object({"node_path": SCENE_NODE}),
    # navigation
    "setup_navigation_region": _object(
        {
            "is_3d": TRUE,
            **_configured_child("NavigationRegion", "NavigationRegion3D or NavigationRegion2D"),
            "properties": dict(PROPERTIES, description="Property values for the node."),
        }
    ),
    "setup_navigation_agent": _object(
        {
            "is_3d": TRUE,
            **_configured_child("NavigationAgent", "NavigationAgent3D or NavigationAgent2D"),
            "properties": dict(PROPERTIES, description="Property values for the node."),
        }
    ),
    "bake_navigation_mesh": _object(
        {
            "node_path": dict(
                SCENE_NODE,
                description="A NavigationRegion2D or NavigationRegion3D; "
                "empty or '.' is the scene root.",
            )
        }
    ),
    "set_navigation_layers": _object(
        {
            "node_path": SCENE_NODE,
            "layers": {
                "type": "integer",
                "minimum": 0,
                "default": 1,
                "description": "navigation_layers bits.",
            },
        }
    ),
    "get_navigation_info": _object({"node_path": SCENE_NODE}),
    "query_navigation_path": _object(
        {
            "node_path": dict(
                SCENE_NODE,
                description="A Node2D or Node3D whose world's navigation map is queried.",
            ),
            "from": dict(POINT_OR_3D, description="Start [x, y] or [x, y, z], default the origin."),
            "to": dict(POINT_OR_3D, description="End [x, y] or [x, y, z], default the origin."),
            "optimize": TRUE,
        }
    ),
    # audio
    "add_audio_player": _object(
        {
            "type": {
                "type": "string",
                "enum": ["AudioStreamPlayer", "AudioStreamPlayer2D", "AudioStreamPlayer3D"],
                "default": "AudioStreamPlayer",
            },
            **_child("the player class"),
            "properties": INITIAL,
            "stream_path": dict(PATH, description="An existing .wav, .ogg or .mp3 to assign."),
        }
    ),
    "add_audio_bus": _object(
        {
            "name": dict(STRING, description="New bus name."),
            "index": {
                "type": "integer",
                "minimum": -1,
                "default": -1,
                "description": "Position; -1 appends.",
            },
        },
        "name",
    ),
    "add_audio_bus_effect": _object(
        {
            "bus": dict(STRING, default="Master"),
            "effect_type": dict(
                STRING, default="AudioEffectReverb", description="AudioEffect class."
            ),
            "properties": dict(
                PROPERTIES, description="Initial values for the effect's properties."
            ),
            "index": {
                "type": "integer",
                "minimum": -1,
                "default": -1,
                "description": "Position; -1 appends.",
            },
        }
    ),
    "set_audio_bus": _object(
        {
            "bus": dict(
                STRING, default="Master", description="Bus name; fields left out stay unchanged."
            ),
            "volume_db": {"type": "number"},
            "mute": {"type": "boolean"},
            "solo": {"type": "boolean"},
            "bypass": {"type": "boolean", "description": "Bypass the bus effects."},
        }
    ),
    "get_audio_bus_layout": _object({}),
    "get_audio_info": _object({"node_path": SCENE_NODE}),
    # tilemap
    "tilemap_set_cell": _object(
        {"node_path": TILEMAP_LAYER, "cell": dict(CELL, default=[0, 0]), **TILE},
        "source_id",
        "atlas_coords",
    ),
    "tilemap_fill_rect": _object(
        {
            "node_path": TILEMAP_LAYER,
            "position": dict(CELL, default=[0, 0], description="Top-left cell."),
            "size": dict(CELL, default=[1, 1], description="Width and height in cells."),
            **TILE,
        },
        "source_id",
        "atlas_coords",
    ),
    "tilemap_get_cell": _object({"node_path": TILEMAP_LAYER, "cell": dict(CELL, default=[0, 0])}),
    "tilemap_clear": _object({"node_path": TILEMAP_LAYER}),
    "tilemap_get_info": _object({"node_path": TILEMAP_LAYER}),
    "tilemap_get_used_cells": _object({"node_path": TILEMAP_LAYER}),
    # theme-ui
    "create_theme": _object(
        {
            "path": dict(
                PATH, description="New Theme .tres or .res file; an existing file is replaced."
            )
        },
        "path",
    ),
    "set_theme_color": _object(
        {
            "path": THEME,
            "type": THEME_TYPE,
            "item": THEME_ITEM,
            "value": dict(
                STRING, default="#ffffffff", description="Color string, such as #ff8800ff or red."
            ),
        },
        "path",
        "item",
    ),
    "set_theme_constant": _object(
        {
            "path": THEME,
            "type": THEME_TYPE,
            "item": THEME_ITEM,
            "value": {"type": "integer", "default": 0},
        },
        "path",
        "item",
    ),
    "set_theme_font_size": _object(
        {
            "path": THEME,
            "type": THEME_TYPE,
            "item": THEME_ITEM,
            "value": {"type": "integer", "default": 16},
        },
        "path",
        "item",
    ),
    "set_theme_stylebox": _object(
        {
            "path": THEME,
            "type": THEME_TYPE,
            "item": THEME_ITEM,
            "properties": dict(PROPERTIES, description="StyleBoxFlat property values."),
        },
        "path",
        "item",
    ),
    "get_theme_info": _object({"path": THEME, "type": THEME_TYPE}, "path"),
    # shader
    "create_shader": _object(
        {
            "path": dict(PATH, description="New .gdshader file; an existing file is replaced."),
            "shader_type": {
                "type": "string",
                "enum": ["canvas_item", "spatial", "particles", "sky", "fog"],
                "default": "canvas_item",
            },
            "source": dict(
                SOURCE, description="Shader text, default an empty shader of shader_type."
            ),
        },
        "path",
    ),
    "read_shader": _object({"path": dict(PATH, description="An existing .gdshader file.")}, "path"),
    "edit_shader": _object(_text_edit("An existing .gdshader file."), "path"),
    "assign_shader_material": _object(
        {
            "node_path": dict(
                SCENE_NODE,
                description="A CanvasItem or GeometryInstance3D; empty or '.' is the scene root.",
            ),
            "shader_path": dict(PATH, description="An existing .gdshader file."),
        },
        "shader_path",
    ),
    "set_shader_param": _object(
        {
            "node_path": SHADER_NODE,
            "parameter": dict(STRING, description="Shader uniform name."),
            "value": VALUE,
        },
        "parameter",
        "value",
    ),
    "get_shader_params": _object({"node_path": SHADER_NODE}),
    # resource
    "read_resource": _object(
        {"path": dict(PATH, description="An existing .tres or .res file.")}, "path"
    ),
    "edit_resource": _object(
        {
            "path": dict(PATH, description="An existing .tres or .res file."),
            "properties": dict(PROPERTIES, description="New values for existing properties."),
        },
        "path",
        "properties",
    ),
    "create_resource": _object(
        {
            "path": dict(PATH, description="New .tres or .res file; an existing file is replaced."),
            "type": dict(STRING, default="Resource", description="Godot Resource class."),
            "properties": dict(
                PROPERTIES, description="Initial values; unknown properties are ignored."
            ),
        },
        "path",
    ),
    "get_resource_preview": _object(
        {"path": dict(PATH, description="An existing resource file.")}, "path"
    ),
    "add_autoload": _object(
        {
            "name": dict(STRING, description="Autoload name, without '/'."),
            "path": dict(PATH, description="An existing .gd or .tscn file."),
        },
        "name",
        "path",
    ),
    "remove_autoload": _object({"name": STRING}, "name"),
    # batch-refactor
    "find_nodes_by_type": _object({"type": NODE_TYPE}),
    "find_signal_connections": _object({}),
    "batch_set_property": _object(
        {"type": NODE_TYPE, "property": STRING, "value": VALUE}, "property", "value"
    ),
    "find_node_references": _object(SEARCH, "query"),
    "get_scene_dependencies": _object(
        {"path": dict(PATH, description="An existing .tscn or .scn file.")}, "path"
    ),
    "cross_scene_set_property": _object(
        {"type": NODE_TYPE, "property": STRING, "value": VALUE}, "property", "value"
    ),
    "find_script_references": _object(SEARCH, "query"),
    "detect_circular_dependencies": _object({}),
    # analysis
    "analyze_scene_complexity": _object({}),
    "analyze_signal_flow": _object({}),
    "find_unused_resources": _object({}),
    "get_project_statistics": _object({}),
    # testing-qa
    "run_test_scenario": _object(
        {
            "steps": {
                "type": "array",
                "items": _object(
                    {
                        "action": dict(STRING, description="A runtime tool name."),
                        "params": dict(PROPERTIES, description="That tool's arguments."),
                    },
                    "action",
                ),
                "maxItems": 100,
            }
        },
        "steps",
    ),
    "assert_node_state": _object(
        {
            "node_path": RUNTIME_NODE,
            "equals": dict(PROPERTIES, description="Property values the node must have."),
        }
    ),
    "assert_screen_text": _object(
        {
            "text": dict(
                STRING, description="Case-insensitive text a visible Control must contain."
            ),
            **UI_PAGE,
        },
        "text",
    ),
    "compare_screenshots": _object(
        {
            "first": dict(PATH, description="An existing .png file."),
            "second": dict(PATH, description="An existing .png file of the same size."),
            "threshold": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "default": 0.01,
                "description": "Channel difference above which a pixel counts as different.",
            },
            "sample_step": {
                "type": "integer",
                "minimum": 1,
                "default": 1,
                "description": "Sample every Nth pixel on each axis.",
            },
        },
        "first",
        "second",
    ),
    "run_stress_test": _object(
        {"frames": {"type": "integer", "minimum": 1, "maximum": 120, "default": 60}}
    ),
    "get_test_report": _object({}),
    # profiling
    "get_performance_monitors": _object({}),
    "get_editor_performance": _object({}),
    # export
    "list_export_presets": _object({}),
    "export_project": _object(
        {
            "preset": dict(STRING, description="Export preset name."),
            "path": {
                "type": "string",
                "maxLength": 500,
                "description": "Output file relative to the project folder, "
                "without res:// or '..'.",
            },
            "debug": dict(FALSE, description="Export a debug build."),
        },
        "preset",
        "path",
    ),
    "get_export_info": _object({}),
}


def _tool_yaml(category: str, name: str, description: str) -> str:
    read_only = name.startswith(READ_ONLY_PREFIXES)
    destructive = name in DESTRUCTIVE
    affinity = "any" if (category, name) in REMOTE_BRIDGE_ANY_AFFINITY else "main"
    if name == "execute_typed_action":
        schema = TYPED_ACTION_INPUT_SCHEMA
        output_schema = json.dumps(TYPED_ACTION_OUTPUT_SCHEMA, separators=(",", ":"))
    elif name == "execute_game_script":
        schema = COMPATIBILITY_METHOD_INPUT_SCHEMA
        output_schema = "{type: object}"
    elif name in TOOL_INPUT_SCHEMAS:
        schema = TOOL_INPUT_SCHEMAS[name]
        output_schema = "{type: object}"
    else:
        schema = {
            "type": "object",
            "properties": CATEGORY_PROPERTIES[category],
            "additionalProperties": True,
        }
        output_schema = "{type: object}"
    input_schema = json.dumps(schema, separators=(",", ":"))
    aliases = ""
    if name in TOOL_SEARCH_ALIASES:
        aliases = f"\n    search_aliases: {json.dumps(TOOL_SEARCH_ALIASES[name])}"
    return f"""  - name: {name}
    description: {description} Parameters are validated again by the Godot host.
    input_schema: {input_schema}
    output_schema: {output_schema}
    read_only: {str(read_only).lower()}
    destructive: {str(destructive).lower()}
    idempotent: {str(read_only).lower()}
    execution: sync
    affinity: {affinity}
    enforce_thread_affinity: true
    timeout_hint_secs: 60
    source_file: scripts/dispatch.py{aliases}
"""


def generate() -> None:
    for category, tools in CATEGORIES.items():
        skill_name = f"godot-{category}"
        skill_dir = ROOT / skill_name
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "dispatch.py").write_text(SCRIPT, encoding="utf-8", newline="\n")
        descriptions = " ".join(description for _, description in tools)
        search_names = " ".join(name for name, _ in tools if name != "execute_game_script")
        runtime_guidance = ""
        if category == "runtime":
            runtime_guidance = (
                "\n\nFor playtest or future RL control, use `execute_typed_action` only. "
                "The host verifies the exact effect; rejected and cancelled actions do not "
                "consume authority. A digest-bound host intent is authorized before runtime "
                "mutation, so a delayed commit after terminal timeout is rejected. "
                "`execute_game_script` is compatibility-only broad public-method execution; "
                "it is not allowlisted and is never the typed action path. "
                "Polling reads accept `budget_ms` (1-50, default 40). A response with "
                "`budget_exceeded: true` is an incomplete page and must be resumed with its "
                "opaque `next_cursor`; never treat it as a complete snapshot."
            )
        if category == "editor":
            runtime_guidance = (
                "\n\nScreenshots copy pixels on the Godot thread and finalize PNG encoding in the "
                "adapter. Responses include measured `elapsed_ms`, `budget_ms`, and "
                "`budget_exceeded`; the budget is fail-closed for traversal work but cannot "
                "preempt user GDScript. Use `chunked=true` and caller-provided cursors for "
                "long editor scripts."
            )
        skill_md = f"""---
name: {skill_name}
description: >-
  Domain skill — {descriptions}
license: MIT
compatibility: "Godot 4.4+; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: godot
    layer: domain
    version: "0.1.0"
    search-hint: "Godot {category} {search_names}"
    tags: "godot,{category},game-development"
    tools: tools.yaml
---

# Godot {category.replace("-", " ").title()}

Use these editor-integrated tools after opening the target Godot project. Paths must remain under `res://`.{runtime_guidance}
"""
        if category == "export":
            skill_md = """---
name: godot-export
description: >-
  Domain skill — Inspect export presets and templates, package Godot projects
  for desktop, Web, and mobile targets, and validate packaged-only resource,
  font, signing, and hosting failures. Use for export planning and release
  preflight, not for editing gameplay or scene content.
license: MIT
compatibility: "Godot 4.4+; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: godot
    layer: domain
    version: "0.2.0"
    search-hint: "__EXPORT_SEARCH_HINT__"
    tags: "godot,export,game-development"
    tools: tools.yaml
    skill-reference-docs:
      - "references/*.md"
---

# Godot Export

Use these editor-integrated tools after opening the target Godot project. Start
with `get_export_info` and `list_export_presets`; do not mutate a preset or
attempt a release export until the requested target and matching template are
known. Paths passed to the tools must remain under `res://`.

Read [Cross-platform packaging](references/platform-packaging.md) before
planning a release build, changing platform presets, or diagnosing a failure
that appears only after export. In particular, editor success is not release
evidence: launch the exported artifact on the target runtime and verify fonts,
resources, storage, input, and startup diagnostics.
"""
            skill_md = skill_md.replace(
                "__EXPORT_SEARCH_HINT__",
                "Godot export package release Windows macOS Linux Web Android iOS fonts CJK "
                "resources presets templates",
            )
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8", newline="\n")
        tools_yaml = "tools:\n" + "".join(_tool_yaml(category, *tool) for tool in tools)
        (skill_dir / "tools.yaml").write_text(tools_yaml, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate()
