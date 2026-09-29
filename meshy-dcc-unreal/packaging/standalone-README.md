# Meshy DCC Unreal standalone sidecar

This package includes its own Python interpreter and `meshy-dcc-server`. A system
Python installation is not required.

## Windows installation

The recommended installer verifies the release checksums, installs the package
under `%LOCALAPPDATA%\meshy-dcc-unreal\standalone`, and configures
`MESHY_DCC_SERVER_EXECUTABLE`:

```powershell
irm https://raw.githubusercontent.com/meshy-dev/meshy-dcc-unreal/main/scripts/install-standalone.ps1 | iex
```

Restart Unreal Editor after installation. The plugin selects this sidecar
automatically on Unreal Engine 4.x and whenever the PythonScriptPlugin is
unavailable.

## Manual installation

1. Extract the archive to a stable directory.
2. Verify each file against `SHA256SUMS`.
3. Set `MESHY_DCC_SERVER_EXECUTABLE` to the absolute path of the bundled
   `meshy-dcc-unreal` launcher. It starts native tool discovery before handing
   off to `meshy-dcc-server`.
4. Install the matching `MeshyDccUnreal` plugin release in your project or engine.
5. Restart Unreal Editor.

Run `meshy-dcc-unreal --version` from this directory to verify the packaged
launcher. Set `MESHY_DCC_UNREAL_RUNTIME=sidecar` to force the standalone runtime,
or `MESHY_DCC_UNREAL_RUNTIME=python` only when the engine embeds Python 3.9 or
newer.
