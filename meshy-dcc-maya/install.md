# Install Meshy DCC for Maya

Not verified on a real Maya yet; experimental.

## Requirements

- Autodesk Maya 2025 or 2026 (Python 3.11). The core wheel is abi3 for
  Python 3.8+, so Maya 2023 and 2024 may load it too, but they are untested;
  on macOS only arm64 builds of Maya can load the arm64 package.
- `meshy-dcc-core>=0.2.0,<0.3.0`, which the package carries.

## With meshy-dcc

```sh
meshy-dcc install --dcc-type maya --execute
```

Pass `--dcc-path` with the Maya executable when several are installed
(`/Applications/Autodesk/maya2026/Maya.app`, or
`C:\Program Files\Autodesk\Maya2026\bin\maya.exe`). The install:

1. downloads the package for this platform and checks its SHA-256;
2. extracts it into the Meshy DCC data folder,
   `adapters/meshy-dcc-maya/meshy-dcc-maya-<platform>/` (on macOS under
   `~/Library/Application Support/meshy-dcc/`, on Windows under
   `%APPDATA%\meshy-dcc\`, or `MESHY_DCC_DATA_DIR`);
3. runs `bin/meshy-dcc-maya uninstall --json`, then
   `bin/meshy-dcc-maya install --json`;
4. records how `meshy-dcc start-instance` launches Maya.

The installer writes one file, `meshy_dcc_maya.mod`, into the first of:

- `MESHY_DCC_MAYA_MODULES_DIR`;
- `$MAYA_APP_DIR/modules`;
- macOS `~/Library/Preferences/Autodesk/maya/modules`, Windows
  `<Documents>\maya\modules` (the Documents known folder, which may be
  redirected, for example to OneDrive).

The file reads:

```
+ meshy_dcc_maya 0.1.1 <extracted package>/module
PYTHONPATH+:=python
```

It applies to every Maya version that reads that folder. The user's own
`userSetup.py`, `Maya.env` and preferences are not touched. Close Maya
before reinstalling on Windows: Maya keeps the module's files open.

## What happens in Maya

Maya adds the module's `plug-ins` and `scripts` folders to its paths and
`python` to `PYTHONPATH`, and runs the module's `scripts/userSetup.py` at
startup. It loads `meshy_dcc_maya_plugin`, which starts the adapter's server
on a free loopback port and registers the session with the `meshy-dcc`
registry. A Maya started by `meshy-dcc start-instance` also offers a safe
stop.

Off unless set before Maya starts:

| Variable | Effect |
|---|---|
| `MESHY_DCC_MAYA_SIDECAR=1` | Run a `meshy-dcc-server` sidecar next to Maya. It opens no LAN listener unless you also set `MESHY_DCC_GATEWAY_REMOTE_PORT` above 0 and `MESHY_DCC_GATEWAY_REMOTE_HOST` to `0.0.0.0` or a LAN address (the default host is loopback). The gateway has no authentication. |
| `MESHY_DCC_MAYA_DISABLE_AUTOSAVE=1` | Turn Maya's AutoSave off while the plug-in is loaded. Maya keeps that switch in the user's preferences. |
| `MESHY_DCC_MAYA_COMMANDPORT_HYGIENE=1` | Close Maya's default commandPort and turn off the security warning on open ones. |

## Remove

```sh
<extracted package>/bin/meshy-dcc-maya uninstall --json
```

removes `meshy_dcc_maya.mod`, only if Meshy DCC wrote it. Then delete the
extracted package folder. A reinstall runs the same command first.
