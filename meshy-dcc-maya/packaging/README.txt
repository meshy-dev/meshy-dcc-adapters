Meshy DCC-Maya — Maya Module Distribution
========================================

Offline Maya .mod module package. Contains the MCP Streamable HTTP
server plugin, the Python dependencies needed by the in-process Maya
bridge (including meshy-dcc-core), and the meshy-dcc-server sidecar binary
used by the default gateway path.

Requirements
------------
- Autodesk Maya 2022, 2023, 2024, 2025, or 2026 (matching platform ZIP; Maya 2022 requires python37/, available in Windows/Linux packages)
- Bundled meshy-dcc-server >= 0.18.21 for default sidecar gateway mode

Version metadata
----------------
module-info.json records adapter_version, embedded_core_version, and
bundled_server_version. embedded_core_version may be older than the CLI or
gateway version; for this release line it is pinned to 0.19.4 to preserve
Maya 2022 / Python 3.7 compatibility.

Installation
------------
1. Unzip the archive to any location.
2. Open the extracted meshy-dcc-maya folder.
3. Double-click install.bat (Windows) or run install.sh (Linux/macOS).
4. Start Maya — the plugin loads automatically via userSetup.py.

The installer generates a .mod file pointing to the extracted location
and deploys userSetup.py to your Maya scripts directory. The module
files stay where you extracted them — only the .mod pointer is copied.

Sidecar runtime
---------------
Default plugin mode starts the bundled meshy-dcc-server sidecar and exposes
the gateway at http://127.0.0.1:19765/mcp.

Clean-machine verification:

  mayapy -c "from meshy_dcc_maya.sidecar import resolve_sidecar_binary; print(resolve_sidecar_binary())"

Alternative deployment options:

- Set MESHY_DCC_SERVER_BIN to the full meshy-dcc-server executable path.
- Put meshy-dcc-server on PATH before launching Maya.
- Set MESHY_DCC_MAYA_SIDECAR=0 before loading the plugin to use the
  legacy in-process gateway path instead.

Uninstallation
--------------
Double-click uninstall.bat (Windows) or run uninstall.sh (Linux/macOS).
This removes the .mod file from your Maya modules directory. The
extracted module folder is not deleted.

Alternatively, load manually via:
  Window > Settings/Preferences > Plug-in Manager > meshy_dcc_maya

Configuration
-------------
Environment variables (optional):

  MESHY_DCC_MAYA_PORT        TCP port for the MCP server. Default: 0 (OS-assigned)
  MESHY_DCC_MAYA_SERVER_NAME Server name in MCP initialize. Default: maya-mcp
  MESHY_DCC_GATEWAY_PORT     Gateway port. Default: 19765
  MESHY_DCC_MAYA_SIDECAR     0 disables the default sidecar process
  MESHY_DCC_SERVER_BIN       Explicit path to the meshy-dcc-server binary
  MESHY_DCC_MAYA_SKILL_PATHS Additional skill search paths (; separated)
  MESHY_DCC_SKILL_PATHS      Global skill search paths (; separated)

Troubleshooting
---------------
- If the plugin does not appear in Plug-in Manager, verify the .mod
  file exists at: <User Documents>/maya/modules/meshy_dcc_maya.mod
- Check the Maya Script Editor output window for error messages.
- Ensure the ZIP matches your platform (win64 / linux / macos).

For more information: https://github.com/meshy-dev/meshy-dcc-maya
