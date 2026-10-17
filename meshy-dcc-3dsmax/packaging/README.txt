Meshy DCC-3dsMax - Drag-and-Drop MZP Installer
============================================

This package installs the meshy-dcc-3dsmax Python adapter plus bundled
meshy-dcc-core and meshy-dcc-server runtime files into the current user's
3ds Max scripts folder.

Maintained MZP scripts live in packaging/templates/. The assembler copies
meshy_dcc_3dsmax_startup.ms into the payload and renders install.ms at package
time.

Installation
------------
1. Start 3ds Max.
2. Drag meshy-dcc-3dsmax-<version>-win64.mzp into the 3ds Max viewport.
3. The installer writes the startup script, activates the new version, removes
   obsolete payload directories where possible, and starts the runtime.
4. Future 3ds Max launches start the runtime automatically. Use the
   Meshy DCC menu only when you need to stop or manually restart it.

The installer copies each payload into an isolated version directory:
  <user scripts>/meshy_dcc_3dsmax/versions/<version-id>

The active version is recorded in:
  <user scripts>/meshy_dcc_3dsmax/current.txt

It also writes a startup MaxScript that adds the installed Python package
directory to sys.path on launch, installs the Meshy DCC menu, cleans obsolete
payload directories, and starts the runtime from the active payload.

Normal MZP installs do not need MESHY_DCC_3DSMAX_PORT or MESHY_DCC_GATEWAY_PORT;
the runtime uses default ports.

Uninstall cleanup uses meshy-dcc-core's import-light install lifecycle helpers
when they are available. If a loaded native extension keeps files locked, the
installer leaves a deferred cleanup marker and finishes removal after restart.

Rez / pipeline deployments
--------------------------
The startup script can also use package roots supplied by the launch
environment instead of copied MZP payloads. Set one or more of:

  MESHY_DCC_3DSMAX_BOOTSTRAP_PATHS  Semicolon-separated Python import roots.
  MESHY_DCC_PYTHONPATHS             Shared semicolon-separated Python import roots.
  MESHY_DCC_3DSMAX_ROOT             Adapter package root.
  MESHY_DCC_CORE_ROOT               meshy-dcc-core package root.
  MESHY_DCC_SERVER_ROOT             Fallback meshy-dcc-server package root.
  MESHY_DCC_SERVER_BIN              Explicit meshy-dcc-server executable for sidecar mode.

For example, a Rez package can point these roots at package-cache paths such as:

  <package-cache>/meshy_dcc_core
  <package-cache>/meshy_dcc_3dsmax
  <package-cache>/meshy_dcc_server

When a root contains a python/, python37/, src/, or package-parent layout, the
startup script adds the appropriate existing directories to sys.path. Python
3.8+ hosts skip explicit python37 roots so they do not load the Python 3.7-only
native core extension.

Smoke Test
----------
Open the MAXScript Listener and run:

  python.Execute "import meshy_dcc_3dsmax; print(meshy_dcc_3dsmax.__version__)"

To start the server:

  Meshy DCC > Start Server

Uninstall
---------
Drag the MZP into 3ds Max and choose Uninstall. The uninstall action stops the
running server, removes the startup script, and deletes the install root. If
loaded native files are still locked, removal is retried during the next 3ds Max
startup from a marker outside the install root.

Manual cleanup paths, if needed:

  <user scripts>/meshy_dcc_3dsmax
  <user scripts>/meshy_dcc_3dsmax_uninstall_pending
  <user startup scripts>/meshy_dcc_3dsmax_startup.ms

For more information:
https://github.com/meshy-dev/meshy-dcc-3dsmax
