---
name: meshy-dcc-houdini-setup
description: |-
  Set up meshy-dcc-houdini for an agent or operator: install Houdini Python
  dependencies with hython, generate MCP host configuration, guide the user
  through the Houdini package / 123.py autostart load step, and run a first
  live-tool smoke prompt.
license: MIT
allowed-tools: Bash Read
metadata:
  meshy-dcc:
    dcc: houdini
    layer: operator
    stage: bootstrap
    version: 1.0.0
    tags:
    - houdini
    - mcp
    - setup
    - hython
    - autostart
---
# meshy-dcc-houdini setup

Use this skill when a user wants an agent to prepare a machine so any MCP
host can use `meshy-dcc-houdini` with SideFX Houdini.

This is an operator skill, not a Houdini runtime skill. Do not load it through
the Houdini MCP server. Run it from the repository checkout or copy its steps
into another agent's instructions.

End users install the adapter with `meshy-dcc install --dcc-type houdini`
(see `install.md` in this directory); that path needs none of the steps below.
This skill is the developer setup from a source checkout of
`meshy-dev/meshy-dcc-adapters` (`meshy-dcc-houdini/`).

## Goal

End with:

- `meshy-dcc-houdini` and its pip dependencies installed into the target Houdini
  `hython` environment.
- An MCP host config snippet that points to the Houdini MCP server.
- The user guided to install the Houdini package so `scripts/123.py` autostarts
  the server (or to start it manually from `hython`).
- A live smoke prompt that proves the agent can discover and call Houdini tools.

## Fast Path

From the repository root, run:

```bash
python skills/meshy-dcc-houdini-setup/scripts/setup_meshy_dcc_houdini.py
```

The script:

1. Finds `hython` from `--hython`, `HYTHON`, `MESHY_DCC_HOUDINI_HYTHON`, `PATH`,
   or common Side Effects Software install locations.
2. Installs this checkout into Houdini: `hython -m pip install -e .`
   (`meshy-dcc-houdini` defines no runtime extra; `meshy-dcc-core` is pulled in
   automatically).
3. Verifies `import meshy_dcc_houdini`.
4. Writes reusable MCP JSON snippets and a smoke prompt under
   `.meshy-dcc/agent-setup/`.

If discovery fails, ask the user for the full `hython` path and re-run:

```bash
python skills/meshy-dcc-houdini-setup/scripts/setup_meshy_dcc_houdini.py --hython "C:\Program Files\Side Effects Software\Houdini 20.5.487\bin\hython.exe"
```

## MCP Configuration

The Houdini `123.py` autostart hook starts the embedded MCP server on the direct
port by default. Configure the MCP host with:

```json
{
  "mcpServers": {
    "houdini": {
      "url": "http://127.0.0.1:19765/mcp"
    }
  }
}
```

Use `http://127.0.0.1:19765/mcp` only when running multiple Houdini sessions
behind the auto-gateway (`MESHY_DCC_GATEWAY_PORT=19765`).

When editing an existing MCP config, preserve unrelated servers. Merge only the
`houdini` server entry unless the user asks for a different server name.

## User Hand-Off: Load the Houdini Package / Autostart

After pip setup and MCP JSON generation, tell the user to make the server start
with Houdini. The recommended path is the bundled Houdini package:

1. Install the Houdini package (`meshy-dcc install --dcc-type houdini`, or
   `bin/meshy-dcc-houdini install --dcc-path <houdini>` from an extracted
   release zip). It writes a `meshy_dcc_houdini.json` package file pointing at
   the package root.
2. The package adds its `houdini/` directory to `HOUDINI_PATH`; once the UI is
   ready, `pythonX.Ylibs/uiready.py` starts the server.
3. Start Houdini and watch the console / shell for the exact OS-assigned
   instance URL. Agents normally connect through the stable gateway on `19765`.

To run from a manual `hython` session instead of the package autostart:

```python
import meshy_dcc_houdini
server = meshy_dcc_houdini.start_server()
print(server.mcp_url)  # Exact direct endpoint selected by the OS
```

Set `MESHY_DCC_HOUDINI_AUTOSTART=0` to disable package autostart.

## First Live Smoke Prompt

Ask the MCP host to run this prompt after Houdini is open and the server is
running:

```text
Use the Houdini MCP server. First call dcc_capability_manifest with loaded_only=false.
Then load the houdini-nodes skill, create a geo node named mcp_setup_smoke_geo
under /obj, list the obj-level nodes, and tell me the MCP URL and created node path.
Use typed tools where available and avoid execute_python unless no typed tool fits.
```

Expected behavior:

- The agent discovers capabilities without dumping every schema.
- The agent loads `houdini-nodes`.
- The agent calls `houdini_nodes__create_node` with `parent_path=/obj`,
  `node_type=geo`, `node_name=mcp_setup_smoke_geo`.
- The new node appears in the Houdini scene.
- `houdini_scene__list_obj_nodes` confirms it exists.

## Troubleshooting

- `hython` not found: ask for the exact Houdini version and the
  `bin/hython` path, then pass `--hython`.
- Pip bootstrap fails: run `hython -m ensurepip --upgrade`, then repeat install.
- MCP connection refused: Houdini is not running, autostart is disabled
  (`MESHY_DCC_HOUDINI_AUTOSTART=0`), or the stable gateway on `19765` is not
  running. Use `meshy-dcc list` to inspect direct URLs.
- Tool missing: call `dcc_capability_manifest` or `search_skills`, then
  `load_skill("<skill-name>")`.
- Autostart silent: check the Houdini console for a
  `meshy-dcc-houdini autostart failed` line and confirm the package JSON points at
  the correct package root.
