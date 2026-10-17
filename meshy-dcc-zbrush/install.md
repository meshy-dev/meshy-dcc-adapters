# Install Meshy DCC for ZBrush

Not verified on a real ZBrush yet; experimental.

## Requirements

- ZBrush 2026.1 or newer on macOS arm64 or Windows x64. Installations are
  found at `/Applications/Maxon ZBrush 20*/ZBrush.app` (also under
  `~/Applications`) and `C:\Program Files\Maxon ZBrush 20*\ZBrush.exe`; pass
  `--dcc-path` for any other location or when several versions are installed.
- `meshy-dcc-core >= 0.2.0, < 0.3.0`. The Meshy DCC package carries CPython
  3.11 with Core and this adapter; ZBrush's embedded Python cannot run the
  sidecar (its interpreter is ZBrush itself).

## With Meshy DCC

```bash
meshy-dcc install --dcc-type zbrush --project /path/to/folder --execute
meshy-dcc start-instance --dcc-type zbrush --project /path/to/folder --wait-ready
```

`install` downloads and checks the package, extracts it into the Meshy DCC
adapters directory and runs, with the package's own Python:

```bash
meshy-dcc-zbrush setup-project /path/to/folder --dcc-path <ZBrush> --json
```

`setup-project` accepts only a ZBrush 2026.1+ application signed by Maxon and
writes one file, `<folder>/.meshy-dcc/launch-plan.json` (the `.meshy-dcc`
folder ignores itself for version control). The plan starts
`ZBrush -script <package>/…/meshy_dcc_zbrush/plugin/mcp_socket_bridge.py`.
Running it again rewrites the plan; to remove the setup, delete that file.

When ZBrush runs the bridge, the bridge listens on a free loopback port and
starts `python -m meshy_dcc_zbrush serve --watch-pid <ZBrush pid>
--socket-port <port>` from the package with a per-launch token. The sidecar
registers with `meshy-dcc`, exits when ZBrush exits, and for a
`start-instance` launch offers a safe stop.

Nothing is written into the ZBrush installation, its `ZData`, or ZBrush's user
settings. A ZBrush opened by hand therefore has no bridge.

## Manual path

To attach a ZBrush that is already open, run the packaged bridge from
**ZScript > Python Scripting > Load**
(`<package>/python/…/site-packages/meshy_dcc_zbrush/plugin/mcp_socket_bridge.py`).
It starts the sidecar the same way. Untested; on macOS the bridge's request
pump may keep the Load button busy. Without `start-instance` there is no safe
stop; close ZBrush yourself.

## Stop

```bash
meshy-dcc stop-instance --operation-id <id>                    # refused: ZBrush cannot report unsaved work
meshy-dcc stop-instance --operation-id <id> --discard-unsaved  # only after the user agreed
```

Save first with `zbrush_file__save_project` or `zbrush_file__save_tool`. An
agreed stop ends the ZBrush process that `start-instance` launched.

## Troubleshooting

- `start-instance` times out at registration: set
  `MESHY_DCC_ZBRUSH_BRIDGE_LOG=<file>` before starting and read it; it records
  the bridge port and the sidecar it started.
- A call reports `ZBRUSH_BLOCKED`: ZBrush is inside a native call, possibly a
  dialog that needs a person. Do not retry; ask the user.
- `ZBRUSH_TIMEOUT_STILL_RUNNING`: the request is still running in ZBrush. Do
  not repeat it; wait until `get_session_info` answers.

## Earlier installer

`meshy-dcc-zbrush install|status|verify|uninstall|upgrade --asset-dir <ZBrush
Asset Directory>` is the fork source's receipt-driven installer into a shared
ZBrush startup folder. It is not used by Meshy DCC, its online payload
source does not exist under Meshy, and it is untested here.
