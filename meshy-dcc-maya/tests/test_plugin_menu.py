"""The Meshy DCC menu offers no server lifecycle controls.

A user who clicks Stop or Restart removes the Maya instance the gateway routes
to; Maya's plug-in manager is the way to unload the plug-in.
"""

import test_plugin_env_vars as _plugin_fixtures

mock_maya_modules = _plugin_fixtures.mock_maya_modules
plugin_module = _plugin_fixtures.plugin_module


def _menu_items(mock_maya_modules):
    return [call[1] for call in mock_maya_modules.cmds.menuItem.call_args_list]


def test_menu_has_no_start_stop_or_restart_item(plugin_module, mock_maya_modules):
    plugin_module._add_menu()

    labels = [item["label"] for item in _menu_items(mock_maya_modules) if "label" in item]
    assert labels, "the menu must still be built"
    assert not [label for label in labels if "MCP Server" in label]


def test_menu_has_no_adjacent_or_edge_dividers(plugin_module, mock_maya_modules):
    plugin_module._add_menu()

    items = _menu_items(mock_maya_modules)
    assert not items[0].get("divider") and not items[-1].get("divider")
    assert not any(left.get("divider") and right.get("divider") for left, right in zip(items, items[1:]))


def test_menu_construction_keeps_internal_lifecycle_functions(plugin_module):
    names = ("_start", "_start_async", "_stop_blocking", "_restart_deferred")
    before = {name: getattr(plugin_module, name) for name in names}

    plugin_module._add_menu()

    assert all(getattr(plugin_module, name) is function for name, function in before.items())
