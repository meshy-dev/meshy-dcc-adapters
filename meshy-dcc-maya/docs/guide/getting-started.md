# Quick Start

Get Maya talking to an MCP host in under 5 minutes.

## Prerequisites

- Maya 2020 or later (Python 3.7+)
- An MCP-compatible host: [Claude Desktop](https://claude.ai/download), [Cursor](https://cursor.sh/), or [OpenClaw](https://github.com/loonghao/openclaw)

## Step 1 — Install

Install into Maya's Python interpreter:

```bash
mayapy -m pip install meshy-dcc-maya
```

For a specific Maya version (Windows example):

```bash
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install meshy-dcc-maya
```

## Step 2 — Load the Maya Plugin

Open Maya, then load `meshy_dcc_maya_plugin.py`:

1. Open **Window > Settings/Preferences > Plug-in Manager**.
2. Browse to or find `maya/plugin/meshy_dcc_maya_plugin.py`.
3. Enable **Loaded**.
4. Enable **Auto load** if Maya should start MCP every session.

The plugin starts the Maya bridge, starts or joins the local gateway, and
installs the Qt dispatcher required by Maya main-thread tools.

For auto-start without the Plug-in Manager, copy or source the bundled
`maya/userSetup.py`. It defers plugin loading until Maya is idle.

## Step 3 — Configure Your MCP Host

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:19765/mcp"
    }
  }
}
```

**File locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop after editing.

### Cursor

In Cursor settings → MCP Servers, add:

```json
{
  "maya": {
    "url": "http://127.0.0.1:19765/mcp"
  }
}
```

### Any MCP Client

Plugin mode exposes one gateway endpoint for MCP hosts:

```
http://127.0.0.1:19765/mcp
```

## Step 4 — Execute Your First Action

In Claude Desktop (or your MCP host), try:

> **"Create a red sphere in Maya"**

Your agent should discover tools, load the needed skills such as
`maya-primitives` and `maya-materials`, then call the typed Maya tools.

Or be more specific:

> **"Create a polygon sphere with radius 2 at position (0, 1, 0) and name it 'ball'"**

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MESHY_DCC_MAYA_PORT` | OS-assigned | Optional fixed TCP port for the MCP instance |
| `MESHY_DCC_MAYA_SERVER_NAME` | `maya-mcp` | Name shown in MCP `initialize` response |
| `MESHY_DCC_MAYA_SKILL_PATHS` | _(empty)_ | Extra skill search roots (`;` on Windows, `:` on Unix); use a root like `{rez_root}/skills` whose children are skill packages |
| `MESHY_DCC_GATEWAY_PORT` | `19765` in plugin mode | Local gateway URL used by MCP hosts |

## Stop the Server

Unload the plugin from Plug-in Manager, or run `import meshy_dcc_maya;
meshy_dcc_maya.stop_server()` if you started the Python server manually.

## Manual Direct Server

Direct `start_server()` is useful for debugging and `mayapy` scripts.
In Maya GUI, pass a UI dispatcher so `affinity: main` tools run on Maya's main
thread:

```python
from meshy_dcc_maya.dispatcher import MayaUiDispatcher, MayaUiPump
import meshy_dcc_maya

dispatcher = MayaUiDispatcher()
MayaUiPump(dispatcher).install()
handle = meshy_dcc_maya.start_server(host_dispatcher=dispatcher)
print(handle.mcp_url())   # exact OS-assigned direct URL
```

Agents normally use the stable gateway on `http://127.0.0.1:19765/mcp`.
Run `meshy-dcc list` when the exact direct URL is required.

## Next Steps

- [Installation Guide](./installation) — plugin mode, userSetup.py, multi-Maya setup
- [MCP Tools Guide](./mcp-tools) — full list of available tools with examples
- [Advanced Usage](./advanced) — custom skills, main-thread scheduling
