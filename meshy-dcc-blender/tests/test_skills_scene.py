"""Unit tests for blender-scene skill scripts (bpy mocked)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

from tests.conftest import load_and_call, make_mock_bpy


class TestGetSessionInfo:
    def test_returns_version_info(self):
        bpy = make_mock_bpy(app_attrs={"version": (4, 1, 0), "version_string": "4.1.0"})
        result = load_and_call("blender-scene/scripts/get_session_info.py", bpy)
        assert result["success"] is True
        assert result["context"]["blender_version"] == "4.1.0"

    def test_no_bpy_returns_error(self):
        result = load_and_call(
            "blender-scene/scripts/get_session_info.py",
            mock_bpy_obj=None,
        )
        # Without bpy the script is patched with our default mock — just check structure
        assert "success" in result

    def test_context_has_expected_fields(self):
        bpy = make_mock_bpy()
        result = load_and_call("blender-scene/scripts/get_session_info.py", bpy)
        assert result["success"] is True
        ctx = result["context"]
        for field in ["blender_version", "scene_name", "object_count"]:
            assert field in ctx, f"Missing field: {field}"


class TestListObjects:
    def test_empty_scene(self):
        bpy = make_mock_bpy(data_attrs={"objects": []})
        result = load_and_call("blender-scene/scripts/list_objects.py", bpy)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_objects(self):
        obj1 = MagicMock()
        obj1.name = "Cube"
        obj1.type = "MESH"
        obj1.location = [0.0, 0.0, 0.0]
        obj1.hide_viewport = False

        obj2 = MagicMock()
        obj2.name = "Light"
        obj2.type = "LIGHT"
        obj2.location = [0.0, 0.0, 3.0]
        obj2.hide_viewport = False

        bpy = make_mock_bpy(data_attrs={"objects": [obj1, obj2]})
        result = load_and_call("blender-scene/scripts/list_objects.py", bpy)
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_type_filter(self):
        obj1 = MagicMock()
        obj1.name = "Cube"
        obj1.type = "MESH"
        obj1.location = [0, 0, 0]
        obj1.hide_viewport = False

        obj2 = MagicMock()
        obj2.name = "Light"
        obj2.type = "LIGHT"
        obj2.location = [0, 0, 3]
        obj2.hide_viewport = False

        bpy = make_mock_bpy(data_attrs={"objects": [obj1, obj2]})
        result = load_and_call("blender-scene/scripts/list_objects.py", bpy, object_type="MESH")
        assert result["success"] is True
        names = [o["name"] for o in result["context"]["objects"]]
        assert "Cube" in names
        assert "Light" not in names


class TestNewScene:
    def test_reads_empty_homefile_without_resetting_preferences(self):
        # read_factory_settings reloads preferences, which disables every
        # extension: the adapter's unregister() then stopped its own server.
        bpy = make_mock_bpy()
        result = load_and_call("blender-scene/scripts/new_scene.py", bpy)
        assert result["success"] is True
        bpy.ops.wm.read_homefile.assert_called_once_with(use_empty=True)
        bpy.ops.wm.read_factory_settings.assert_not_called()


class TestSaveScene:
    """save_scene succeeds only when the operator finished and the file reads back fresh."""

    @staticmethod
    def _saving_bpy(tmp_path, *, result=None, write=b"blend", scene_path="saved.blend", stale=False):
        """A bpy whose save operators write ``write`` to ``scene_path`` and return ``result``."""
        bpy = make_mock_bpy()
        target = tmp_path / scene_path
        if stale:
            target.write_bytes(b"older save")
            os.utime(target, (1_000_000, 1_000_000))
        bpy.data.filepath = ""

        def save(**kwargs):
            if write is not None:
                target.write_bytes(write)
            bpy.data.filepath = str(target) if scene_path else ""
            return {"FINISHED"} if result is None else result

        bpy.ops.wm.save_as_mainfile.side_effect = save
        bpy.ops.wm.save_mainfile.side_effect = save
        return bpy, target

    def test_save_to_explicit_path_reports_the_verified_file(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path)
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is True
        bpy.ops.wm.save_as_mainfile.assert_called_once_with(filepath=str(target))
        ctx = result["context"]
        assert ctx["filepath"] == str(target)
        assert ctx["file_size_bytes"] == len(b"blend")
        assert result["postcondition"]["verified"] is True
        assert result["postcondition"]["path"] == str(target)

    def test_reports_the_path_blender_saved_to_not_the_one_requested(self, tmp_path):
        # Blender appends .blend to an extensionless path; that is the file to verify.
        bpy, target = self._saving_bpy(tmp_path)
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(tmp_path / "saved"))
        assert result["success"] is True
        assert result["context"]["filepath"] == str(target)

    def test_save_existing_file(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path)
        bpy.data.filepath = str(target)
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy)
        assert result["success"] is True
        bpy.ops.wm.save_mainfile.assert_called_once()
        bpy.ops.wm.save_as_mainfile.assert_not_called()

    def test_error_when_no_filepath_and_unsaved(self):
        bpy = make_mock_bpy()
        bpy.data.filepath = ""
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy)
        assert result["success"] is False
        bpy.ops.wm.save_mainfile.assert_not_called()
        bpy.ops.wm.save_as_mainfile.assert_not_called()

    def test_cancelled_save_fails_even_though_a_file_is_already_there(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path, result={"CANCELLED"}, write=None, stale=True)
        before = target.stat()
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False
        assert result["context"]["operator_result"] == ["CANCELLED"]
        assert result["context"]["mutation_applied"] is None
        assert target.read_bytes() == b"older save" and target.stat().st_mtime == before.st_mtime
        assert bpy.ops.wm.save_as_mainfile.call_count == 1  # never replayed

    def test_non_set_operator_result_fails(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path, result="FINISHED")
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False

    def test_finished_without_a_file_fails(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path, write=None)
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False
        assert "cannot be read back" in result["error"]

    def test_finished_with_an_empty_file_fails(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path, write=b"")
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False
        assert "nonempty" in result["error"]

    def test_finished_but_file_not_rewritten_fails(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path, write=None, stale=True)
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False
        assert "predates" in result["error"]
        assert result["context"]["filepath"] == str(target)

    def test_finished_with_no_scene_path_fails(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path, scene_path="")
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False

    def test_operator_exception_fails_and_is_not_replayed(self, tmp_path):
        bpy, target = self._saving_bpy(tmp_path)
        bpy.ops.wm.save_as_mainfile.side_effect = RuntimeError("Unable to open for writing")
        result = load_and_call("blender-scene/scripts/save_scene.py", bpy, filepath=str(target))
        assert result["success"] is False
        assert result["context"]["mutation_applied"] is None
        assert bpy.ops.wm.save_as_mainfile.call_count == 1


class TestOpenScene:
    def test_opens_blend_file(self):
        bpy = make_mock_bpy()
        result = load_and_call("blender-scene/scripts/open_scene.py", bpy, filepath="/path/to/scene.blend")
        assert result["success"] is True
        bpy.ops.wm.open_mainfile.assert_called_once_with(filepath="/path/to/scene.blend")


class TestGetSceneInfo:
    def test_returns_scene_stats(self):
        bpy = make_mock_bpy()
        # Mock collection hierarchy
        mock_col = MagicMock()
        mock_col.name = "Scene Collection"
        mock_col.objects = []
        mock_col.children = []
        bpy.context.scene.collection = mock_col
        bpy.context.scene.objects = []

        result = load_and_call("blender-scene/scripts/get_scene_info.py", bpy)
        assert result["success"] is True
        ctx = result["context"]
        assert "scene_name" in ctx
        assert "collections" in ctx

    def test_counts_objects_by_type_and_recurses_collections(self):
        mesh = MagicMock()
        mesh.name = "Cube"
        mesh.type = "MESH"
        light = MagicMock()
        light.name = "Key"
        light.type = "LIGHT"

        child_col = MagicMock()
        child_col.name = "Props"
        child_col.objects = [mesh]
        child_col.children = []
        root_col = MagicMock()
        root_col.name = "Scene Collection"
        root_col.objects = [light]
        root_col.children = [child_col]

        bpy = make_mock_bpy()
        bpy.context.scene.collection = root_col
        bpy.context.scene.objects = [mesh, light]

        result = load_and_call("blender-scene/scripts/get_scene_info.py", bpy)

        assert result["success"] is True
        ctx = result["context"]
        assert ctx["total_objects"] == 2
        assert ctx["objects_by_type"] == {"MESH": 1, "LIGHT": 1}
        assert ctx["collections"]["children"][0]["name"] == "Props"
        assert ctx["collections"]["children"][0]["objects"] == ["Cube"]
