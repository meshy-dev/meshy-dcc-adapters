"""MESHY_DCC_MAYA_DISABLE_ARBITRARY_SCRIPT must refuse every code-bearing tool.

A Maya expression string is code: ``cmds.expression(string='python("...")')``
runs the embedded Python in the host. The tests use a synthetic ``maya.cmds``
that only sets an in-memory marker, so nothing is evaluated for real.
"""

from __future__ import annotations

import builtins
import os
import re
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import yaml
from conftest import load_skill_script

from meshy_dcc_maya import _code_policy, _dev_session
from meshy_dcc_maya._env import ENV_DISABLE_ARBITRARY_SCRIPT

MARKER_ATTR = "_meshy_dcc_maya_policy_marker"
MARKER_EXPRESSION = 'python("import builtins; builtins.{} = True")'.format(MARKER_ATTR)
MARKER_SCRIPT_NODE = "import builtins; builtins.{} = True".format(MARKER_ATTR)
POLICY_ON = {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}


@pytest.fixture()
def fake_maya(monkeypatch):
    """Install a ``maya.cmds`` that models code evaluation with an in-memory marker."""
    if hasattr(builtins, MARKER_ATTR):
        delattr(builtins, MARKER_ATTR)
    calls = {"expression": 0, "script_node": 0}
    cmds = MagicMock(name="maya.cmds")
    cmds.objExists.return_value = True
    cmds.ls.return_value = []
    cmds.getAttr.return_value = ""

    def _expression(*args, **kwargs):
        calls["expression"] += 1
        if "python(" in str(kwargs.get("string", "")):
            setattr(builtins, MARKER_ATTR, True)
        return "expressionNode1"

    def _script_node(**kwargs):
        calls["script_node"] += 1
        if "builtins." in str(kwargs.get("beforeScript", "")):
            setattr(builtins, MARKER_ATTR, True)
        return "scriptNode1"

    cmds.expression.side_effect = _expression
    cmds.scriptNode.side_effect = _script_node
    maya_mod = types.ModuleType("maya")
    maya_mod.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    monkeypatch.delenv(ENV_DISABLE_ARBITRARY_SCRIPT, raising=False)
    yield calls
    if hasattr(builtins, MARKER_ATTR):
        delattr(builtins, MARKER_ATTR)


def _assert_refused(result):
    assert result.get("success") is False, result
    assert "policy" in str(result.get("message", "")).lower(), result
    assert not hasattr(builtins, MARKER_ATTR), "code ran despite the policy"


@pytest.mark.parametrize("entry", ["create_expression", "edit_expression"])
@pytest.mark.parametrize("call", ["sdk", "main"])
def test_expression_tools_are_refused(fake_maya, entry, call):
    mod = load_skill_script("maya-expressions", entry)
    kwargs = {"expression": MARKER_EXPRESSION}
    if entry == "edit_expression":
        kwargs["name"] = "expressionNode1"
    with patch.dict(os.environ, POLICY_ON):
        result = getattr(mod, entry)(**kwargs) if call == "sdk" else mod.main(**kwargs)
    _assert_refused(result)
    assert fake_maya["expression"] == 0


@pytest.mark.parametrize("entry", ["create_expression", "edit_expression"])
def test_expression_tools_still_run_when_the_policy_is_unset(fake_maya, entry):
    """Control: the double really models the evaluation path the policy blocks."""
    mod = load_skill_script("maya-expressions", entry)
    kwargs = {"expression": MARKER_EXPRESSION}
    if entry == "edit_expression":
        kwargs["name"] = "expressionNode1"
    assert getattr(mod, entry)(**kwargs).get("success") is True
    assert getattr(builtins, MARKER_ATTR, False) is True


def test_script_node_create_is_refused_but_get_stays_available(fake_maya):
    mod = load_skill_script("maya-scripting", "get_script_node")
    with patch.dict(os.environ, POLICY_ON):
        refused = mod.main(node_name="n", action="create", script=MARKER_SCRIPT_NODE)
        read = mod.main(node_name="n", action="get")
    _assert_refused(refused)
    assert fake_maya["script_node"] == 0
    assert read.get("success") is True, read


def test_introspect_eval_is_refused(fake_maya):
    mod = load_skill_script("maya-scripting", "introspect")
    with patch.dict(os.environ, POLICY_ON):
        _assert_refused(mod.main(expression="1 + 2"))
    assert mod.main(expression="1 + 2").get("success") is True


@pytest.mark.parametrize("skill", ["maya-scripting", "maya-plugins"])
def test_load_plugin_is_refused(fake_maya, skill):
    mod = load_skill_script(skill, "load_plugin")
    with patch.dict(os.environ, POLICY_ON):
        _assert_refused(mod.load_plugin(plugin="fbxmaya"))


@pytest.mark.parametrize("func", ["run_script", "run_entrypoint", "run_check", "reload_modules", "start_debugpy"])
def test_dev_session_run_tools_are_refused(func):
    kwargs = {"run_script": {"script_path": "x.py"}, "run_entrypoint": {"target": "x:y"}}.get(func, {})
    with patch.dict(os.environ, POLICY_ON):
        result = getattr(_dev_session, func)(**kwargs)
    assert result.get("success") is False, result
    assert "policy" in str(result.get("message", "")).lower(), result


def test_read_only_and_typed_tools_are_not_gated(fake_maya):
    mod = load_skill_script("maya-expressions", "list_expressions")
    with patch.dict(os.environ, POLICY_ON):
        assert mod.main(object_name="").get("success") is True
        for tool in ("set_keyframes", "list_expressions", "attach_project", "unload_plugin", "list_plugins"):
            assert _code_policy.arbitrary_script_refusal(tool) is None


def test_policy_accepts_the_documented_truthy_tokens():
    from meshy_dcc_maya._env import resolve_arbitrary_script_disabled

    for token in ("1", "true", "yes", "on"):
        with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: token}):
            assert resolve_arbitrary_script_disabled() is True
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "0"}):
        assert resolve_arbitrary_script_disabled() is False


# Reverse scan of the shipped catalog: every tool script that uses a code
# evaluation primitive must be gated (CODE_BEARING_TOOLS) or reviewed here.
SKILLS_DIR = os.path.join(os.path.dirname(_code_policy.__file__), "skills")
CODE_EVAL_PRIMITIVES = re.compile(
    r"runpy\.run_path|_dev_session\.run_|\bexec\(|\beval\(|cmds\.expression\(|"
    r"cmds\.scriptNode\(|cmds\.loadPlugin\(|mel\.eval\(|importlib\.import_module|"
    r"subprocess\.|\bdebugpy\b|start_debugpy\(|reload_modules\(|os\.system\("
)
SCRIPT_ALIASES = {"maya-scripting/introspect_eval": "introspect.py"}
REVIEWED_NON_CODE_BEARING = {
    **{
        "{}/{}".format(skill, name): "fixed MEL templates and plug-in names filled from typed parameters"
        for skill, names in {
            "maya-geometry": ("export_fbx", "export_obj", "export_alembic", "import_fbx", "import_file"),
            "maya-shot-export": ("export_camera", "export_shot_alembic", "export_shot_fbx"),
            "maya-render": ("render_frame", "render_scene", "setup_hdr_arnold"),
            "maya-import-to-scene": ("import_to_scene",),
            "maya-pipeline": ("publish_asset",),
            "maya-render-setup": ("list_render_layers",),
            "maya-rigging": ("detect_rig_frameworks",),
        }.items()
        for name in names
    },
    "maya-scripting/list_mel_procedures": "fixed globalProcs() query",
    "maya-expressions/list_expressions": "read-only cmds.expression(query=True)",
    "maya-render/playblast_to_mp4": "fixed ffmpeg command, no caller code",
    "maya-render-farm/get_render_job_status": "fixed Deadline command, no caller code",
    "maya-render-farm/submit_to_deadline": "fixed Deadline command, no caller code",
}


def _catalog_hits():
    catalog, hits = set(), {}
    for root, _dirs, files in os.walk(SKILLS_DIR):
        if "tools.yaml" not in files:
            continue
        skill = os.path.basename(root)
        with open(os.path.join(root, "tools.yaml"), "r", encoding="utf-8") as handle:
            spec = yaml.safe_load(handle) or {}
        for tool in spec.get("tools") or []:
            name = tool.get("name")
            if not name:
                continue
            key = "{}/{}".format(skill, name)
            catalog.add(key)
            script = os.path.join(root, "scripts", SCRIPT_ALIASES.get(key, name + ".py"))
            if os.path.isfile(script):
                with open(script, "r", encoding="utf-8") as handle:
                    found = CODE_EVAL_PRIMITIVES.findall(handle.read())
                if found:
                    hits[key] = sorted(set(found))
    return catalog, hits


def test_every_gated_tool_exists_in_the_catalog_and_uses_a_code_primitive():
    catalog, hits = _catalog_hits()
    names = {key.split("/", 1)[1] for key in catalog}
    assert set(_code_policy.CODE_BEARING_TOOLS) <= names
    hit_names = {key.split("/", 1)[1] for key in hits}
    assert set(_code_policy.CODE_BEARING_TOOLS) <= hit_names


def test_no_catalog_tool_uses_a_code_primitive_without_being_gated_or_reviewed():
    catalog, hits = _catalog_hits()
    stale = sorted(set(REVIEWED_NON_CODE_BEARING) - catalog)
    assert not stale, "reviewed entries no longer in the catalog: {}".format(stale)
    ungated = {
        key: primitives
        for key, primitives in hits.items()
        if key.split("/", 1)[1] not in _code_policy.CODE_BEARING_TOOLS and key not in REVIEWED_NON_CODE_BEARING
    }
    assert not ungated, "code-evaluating tools neither gated nor reviewed: {}".format(ungated)
