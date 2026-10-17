# meshy-dcc-zbrush

<p align="center">
  <img src="docs/assets/meshy-dcc-zbrush.svg" alt="Meshy DCC · ZBRUSH" width="600">
</p>

<!-- meshy-dcc-coverage-pointer:start -->
<!-- Generated from meshy-dcc-catalog.yml by scripts/generate_adapter_pointer.py in meshy-dcc/meshy-dcc-core. Do not edit by hand. -->
## Part of the Meshy DCC host matrix

**meshy-dcc-zbrush** — ZBrush adapter for Meshy DCC.

It is one of **47 host adapters** in the Meshy DCC catalog. Every adapter speaks the same
MCP protocol and builds on the same core runtime contract; each one exposes the tools
its own host needs on top of that.

- [All host adapters and install metadata](https://www.meshy.ai/meshy-dcc/ecosystem)
- [Host matrix on the core README](https://github.com/meshy-dev/meshy-dcc-core#readme)
- [Showcase](https://www.meshy.ai/meshy-dcc/showcase)

This block is generated from the catalog entry in
[`meshy-dcc-catalog.yml`](https://github.com/meshy-dev/meshy-dcc-core/blob/main/meshy-dcc-catalog.yml).
Re-run the generator after changing the catalog.
<!-- meshy-dcc-coverage-pointer:end -->

## Agent workflow

AI agents should use the shared gateway through `meshy-dcc`; IDE users may
continue to use the MCP endpoint. Prefer typed skills and tools over raw scripts.

### Install or update the CLI

`meshy-dcc` is the preferred control path for every shell-capable agent. If
it is missing, ask the user before installing the latest official release:

```bash
# Linux/macOS
curl -fsSL https://raw.githubusercontent.com/meshy-dev/meshy-dcc-core/main/scripts/install-cli.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/meshy-dev/meshy-dcc-core/main/scripts/install-cli.ps1 | iex"
```

Keep an official build current through the release manifest:

```bash
meshy-dcc update check
meshy-dcc update apply
```

`update apply` downloads and stages the latest CLI for the next launch. It
does not update a running `meshy-dcc-server`; update that server in its own
environment.

```bash
meshy-dcc dcc-types
meshy-dcc list
meshy-dcc search --query "<task>" --dcc-type zbrush
meshy-dcc describe <tool-slug>
meshy-dcc call <tool-slug> --json '{"key":"value"}'
```

`dcc-types` reports release-catalog support; `list` reports live sessions. If a
tool belongs to an inactive progressive skill, call `meshy-dcc load-skill <skill-name> --dcc-type zbrush` before retrying. For post-task improvement,
attach a stable session id with `--meta-json`, query `meshy-dcc stats --range 24h --session-id <task-id>`, then pass the bounded evidence to the
`review_skill_improvement` prompt from `meshy-dcc-skills-creator`.


[![PyPI](https://img.shields.io/pypi/v/meshy-dcc-zbrush)](https://pypi.org/project/meshy-dcc-zbrush/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange)](https://github.com/meshy-dev/meshy-dcc-zbrush)

ZBrush adapter for the [DCC Model Context Protocol](https://github.com/meshy-dev/meshy-dcc-core) ecosystem.

> **Requires ZBrush 2026.1+** with the official [Python SDK](https://developers.maxon.net/docs/zbrush/py/2026_1_0/index.html) (CPython 3.11 embedded in ZBrush).

## Showcase

![Typed ZBrush workflow validating a five-million-face Fantasy Dragon before OBJ export](docs/images/zbrush-fantasy-dragon-showcase.png)

Real ZBrush 2026 evidence from a typed, quiet high-poly workflow: **2,499,970 points / 5,000,000 faces**, inspected and exported as the active Dragon subtool. Fantasy Dragon model by [Artec 3D](https://www.artec3d.com/3d-models/fantasy-dragon), used under CC BY 4.0; the source model is not included in this repository. See the [full workflow and copyable prompt](https://www.meshy.ai/meshy-dcc/showcase#zbrush-fantasy-dragon).

## Quick install

### 1. Install a fixed wheel version

```bash
python -m pip install "meshy-dcc-zbrush==<version>"
```

The wheel includes the lifecycle CLI and the sidecar bridge payload.

### 2. Plan and apply the plugin install

Set `ZBRUSH_USER_ASSETS_DIR`, then run the standard lifecycle. The installer
requires an explicit ZBrush path so it can prove the 2026.1+ host floor.

```bash
meshy-dcc-zbrush install --version <version> --dcc-path "<ZBrush path>" --python python --dry-run --json
meshy-dcc-zbrush install --version <version> --dcc-path "<ZBrush path>" --python python --yes --json
```

The fixed release payload is SHA-256 verified before caching. Sidecar mode
installs a dedicated module and appends a bounded managed block to the shared
`Python/init.py`; it never overwrites that file. Receipt-backed uninstall and
rollback restore the previous state. Applying an install or upgrade stages a
candidate and returns exit `50`; the candidate is committed only after the
exact ZBrush process, start identity, endpoint, version, and loaded module
origins pass `verify`.

See the [canonical lifecycle SOP](install.md) ([raw URL](https://raw.githubusercontent.com/meshy-dev/meshy-dcc-zbrush/main/install.md)).

### 3. Restart ZBrush

Launch or restart ZBrush, then start the external MCP sidecar:

```bash
meshy-dcc-zbrush --mode sidecar --socket-port 19876
```

The plugin registers a top-level **Meshy DCC** palette through the official
ZBrush Python SDK with these actions:

- **Copy Instance ID**
- **Server Info**
- **About Meshy DCC**

Instance identity belongs to the MCP server. In embedded mode the first two
actions read the public `DccServerBase` runtime context. The standalone
sidecar plugin does not guess identity from environment variables or registry
files; it directs you to `meshy-dcc list` when that external context is not
available in the ZBrush process.

### 4. Verify host readiness

Verify the dynamically allocated instance URL:

```bash
meshy-dcc-zbrush verify --version <version> --dcc-path "<ZBrush path>" --python python --json
meshy-dcc list
```

### 5. Configure your AI client

Add the MCP server to your AI client config (Cursor, Claude Desktop, etc.):

```json
{
  "mcpServers": {
    "zbrush": {
      "url": "http://127.0.0.1:19765/mcp"
    }
  }
}
```

---

## How it works

ZBrush **does not ship a built-in HTTP REST server**. The pre-alpha scaffold that assumed `Preferences > Network > Enable HTTP Server` was incorrect.

The supported integration paths are:

| Mode | When to use | Stack |
|------|-------------|-------|
| **Sidecar + socket plugin** (recommended) | Production GUI and CI clients | External Python → TCP :19876 → main-thread bridge inside ZBrush |
| **Embedded** (advanced) | Pure-Python experiments only | Python plugin inside ZBrush → `zbrush.commands` |

Rust is **not** loaded inside ZBrush. The **`meshy-dcc-core` wheel** (PyO3) runs
in the external sidecar process; importing its extension module into the ZBrush
2026 embedded VM is not a supported runtime path. The ZBrush-facing bridge is
Python only and executes requests serially on the host main thread while
pumping UI updates between requests. Only one SDK request is admitted at a
time; additional requests fail with a retryable busy response, and `ping`
remains available without touching the SDK. A long native operation can still
make Windows report ZBrush as not responding because the Maxon SDK call itself
is synchronous. If a bridge timeout says the request is still running, do not
retry the mutation; poll bridge health until `busy` becomes false. File import,
export, and baking suppress scripted action feedback without wrapping the
native operation in `zbc.freeze()`, so ZBrush can still present progress or a
required native dialog.

GoZ C++ SDK is for **mesh exchange between DCC apps**, not general MCP automation — we do not build the primary adapter on GoZ.

```
Recommended sidecar mode:

AI Agent → Gateway :19765 → OS-assigned MCP instance → ZBrushMcpServer
         → TCP :19876 → mcp_socket_bridge.py (inside ZBrush) → zbrush.commands
```

## Features (v0.2.0)

- `DccServerBase` adapter with progressive skill loading
- Bundled skills: `zbrush-scripting`, `zbrush-scene`, `zbrush-subtool`, `zbrush-brush`, `zbrush-viewport`, `zbrush-interchange`, `zbrush-import-to-scene`
- In-process executor for ZBrush's embedded Python VM
- Optional socket bridge plugin for sidecar deployments
- Top-level Meshy DCC palette registered through `zbrush.commands`
- Gateway election compatible with `meshy-dcc-core`

## Requirements

- ZBrush **2026.1+**
- Python **3.10+** on the sidecar host (ZBrush itself ships 3.11)
- `meshy-dcc-core >= 0.2.0, < 0.3.0`

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MESHY_DCC_ZBRUSH_PORT` | OS-assigned | Optional fixed MCP instance port |
| `MESHY_DCC_ZBRUSH_MODE` | auto | `embedded` or `sidecar` |
| `MESHY_DCC_ZBRUSH_AUTOSTART` | `1` | Auto-start embedded server from plugin |
| `MESHY_DCC_ZBRUSH_SOCKET_PORT` | `19876` | Socket bridge port (sidecar) |
| `MESHY_DCC_GATEWAY_PORT` | `19765` | Gateway election port |
| `MESHY_DCC_MINIMAL` | `1` | Progressive skill loading |

## Bundled skills

| Skill | Tools |
|-------|-------|
| `zbrush-scripting` | `execute_python`, `get_session_info` |
| `zbrush-scene` | `get_scene_info`, `list_subtools` |
| `zbrush-subtool` | `select_subtool`, `get_subtool_status` |
| `zbrush-brush` | `create_wrinkle_brush`, `load_wrinkle_brush` |
| `zbrush-viewport` | `capture_turntable` |
| `zbrush-interchange` | `export_active_subtool_obj` |

## Path concepts

- **PYTHONPATH** — where Python looks for packages (`pip install` handles this)
- **ZBRUSH_USER_ASSETS_DIR** / **ZBRUSH_PLUGIN_PATH** — plugin scan roots used by ZBrush 2026.1+

`pip install meshy-dcc-zbrush` puts the Python package on `PYTHONPATH`. The
lifecycle CLI installs host files transactionally; do not copy a bridge over
the shared `Python/init.py` manually.

## Skill authoring

Skills lazy-import `zbrush.commands` and run on the main thread (`affinity: main`).

```python
from meshy_dcc_core.skill import skill_entry
from meshy_dcc_zbrush.api import import_zbc, with_zbrush, zb_success


@skill_entry
@with_zbrush
def my_tool(**kwargs) -> dict:
    zbc = import_zbc()
    count = zbc.get_subtool_count()
    return zb_success(f"{count} subtool(s)", count=count)
```

## Sidecar mode

After completing the receipt-driven install and restarting ZBrush, run the MCP
server outside ZBrush:

The sidecar can also start first: it retains the bridge endpoint and retries
the connection on the first tool call after ZBrush becomes available.

```bash
meshy-dcc-zbrush --mode sidecar --socket-port 19876
```

## Development

See [docs/development.md](docs/development.md) for source-based setup, testing, and contribution workflow.

## References

- [ZBrush Python SDK 2026.1](https://developers.maxon.net/docs/zbrush/py/2026_1_0/index.html)
- [ZBrush Python environment](https://developers.maxon.net/docs/zbrush/py/2026_1_0/manuals/python_environment.html)
- [GoZ SDK (mesh exchange only)](https://developers.maxon.net/docs/zbrush/goz_sdk.pdf)
- Community reference: [newsbubbles/zbrush-mcp](https://github.com/newsbubbles/zbrush-mcp) (socket bridge pattern)

## License

MIT
