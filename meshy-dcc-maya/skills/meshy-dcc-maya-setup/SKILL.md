---
name: meshy-dcc-maya-setup
description: |-
  Set up meshy-dcc-maya for an agent or operator: install Maya Python
  dependencies with mayapy, generate MCP host configuration, guide the user
  through loading the Maya plugin, and run a first live-tool smoke prompt.
license: MIT
allowed-tools: Bash Read
metadata:
  meshy-dcc:
    dcc: maya
    layer: operator
    stage: bootstrap
    version: 1.0.0
    tags:
    - maya
    - mcp
    - setup
    - mayapy
    - plugin
---
# meshy-dcc-maya setup

Use this skill when a user wants an agent to prepare a machine so any MCP
host can use `meshy-dcc-maya` with Autodesk Maya.

The supported install is `meshy-dcc install --dcc-type maya` (see the root
`install.md`). This skill sets up a source checkout for development only;
`meshy-dcc-maya` is not published on PyPI, so `--source pypi` does not work.

This is an operator skill, not a Maya runtime skill. Do not load it through
the Maya MCP server. Run it from the repository checkout or copy its steps into
another agent's instructions.

If the user says "帮我参考 `meshy-dcc/meshy-dcc-maya/install.md` 去安装", read the
root `install.md` first, then follow this skill.

## Goal

End with:

- `meshy-dcc-maya` and its pip dependencies installed into the target Maya
  `mayapy` environment.
- An MCP host config snippet that points to the Maya plugin gateway.
- The user guided to load `meshy_dcc_maya_plugin.py` in Maya's Plug-in Manager.
- A live smoke prompt that proves the agent can discover and call Maya tools.

## Fast Path

From the repository root, run:

```bash
python skills/meshy-dcc-maya-setup/scripts/setup_meshy_dcc_maya.py
```

The script:

1. Finds `mayapy` from `--mayapy`, `MAYAPY`, `MESHY_DCC_MAYA_MAYAPY`, `PATH`,
   or common Autodesk install locations.
2. Installs this checkout into Maya with the sidecar extra:
   `mayapy -m pip install -e ".[sidecar]"`.
3. Verifies adapter imports and requires the installed Core version to satisfy
   `meshy-dcc-core>=0.2.0,<0.3.0`.
4. Writes reusable MCP JSON snippets under `.meshy-dcc/agent-setup/`.

Use PyPI instead of the local checkout when setting up an end-user machine:

```bash
python skills/meshy-dcc-maya-setup/scripts/setup_meshy_dcc_maya.py --source pypi
```

If discovery fails, ask the user for the full `mayapy` path and re-run:

```bash
python skills/meshy-dcc-maya-setup/scripts/setup_meshy_dcc_maya.py --mayapy "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
```

## MCP Configuration

Plugin sidecar mode is the preferred default. Configure the MCP host with:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:19765/mcp"
    }
  }
}
```

For an explicit direct connection, run `meshy-dcc list` and use the exact
instance URL published there; do not hardcode an instance port.

When editing an existing MCP config, preserve unrelated servers. Merge only the
`maya` server entry unless the user asks for a different server name.

## User Hand-Off: Load the Maya Plugin

After pip setup and MCP JSON generation, tell the user:

1. Open Autodesk Maya.
2. Go to `Window > Settings/Preferences > Plug-in Manager`.
3. Add or find `meshy_dcc_maya_plugin.py`.
4. Check `Loaded`; optionally check `Auto load`.
5. Watch Script Editor output for the MCP URL.

Expected plugin-mode URL is usually `http://127.0.0.1:19765/mcp`.

If the plugin is not visible, verify that `maya/plugin/meshy_dcc_maya_plugin.py`
is on `MAYA_PLUG_IN_PATH` or copy it into the user's Maya plug-ins folder.

## First Live Smoke Prompt

Ask the MCP host to run this prompt after Maya is open and the plugin is
loaded:

```text
Use the Maya MCP server. First call dcc_capability_manifest with loaded_only=false.
Then load the maya-primitives skill, create a sphere named mcp_setup_smoke_sphere
with radius 2, list scene objects, and tell me the MCP URL and created object name.
Use typed tools where available and avoid execute_python unless no typed tool fits.
```

Expected behavior:

- The agent discovers capabilities without dumping every schema.
- The agent loads `maya-primitives`.
- The agent calls `maya_primitives__create_sphere`.
- The new object appears in the Maya scene.
- `maya_scene__list_objects` or another scene query confirms it exists.

## Troubleshooting

- `mayapy` not found: ask for the exact Maya version and mayapy path.
- Pip bootstrap fails: run `mayapy -m ensurepip --upgrade`, then repeat install.
- MCP connection refused: Maya is not running, the plugin is not loaded, or the
  host cached a stale direct URL; use gateway `19765` or refresh with `meshy-dcc list`.
- Tool missing: call `dcc_capability_manifest` or `search_skills`, then
  `load_skill("<skill-name>")`.
- Plugin loaded but hangs: check Script Editor output, firewall/localhost
  rules, and whether a blocking Maya dialog is open.
