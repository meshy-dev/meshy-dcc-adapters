# Install Meshy DCC for Houdini

Not verified on a real Houdini yet; the package is experimental. Everything
below comes from the source and from SideFX's documentation, not from a
Houdini session.

## Requirements

- SideFX Houdini 20.5 or newer (FX, Core, Indie or Apprentice) on macOS Apple
  Silicon or Windows x64. Startup uses `pythonX.Ylibs/uiready.py`, which
  Houdini runs in interactive sessions; 20.5 and 21 ship Python 3.11.
- The `meshy-dcc` CLI. `meshy-dcc-core >= 0.2.0,<0.3.0` ships inside the
  package; nothing is installed into Houdini's Python.
- Write access to the Houdini user preferences directory. The installer never
  touches the Houdini application directory.

## Supported versions

| Platform | Package | Houdini executable it looks for |
|---|---|---|
| macOS (Apple Silicon) | `meshy-dcc-houdini-macos-arm64.zip` | `/Applications/Houdini/Houdini*/Frameworks/Houdini.framework/Versions/Current/Resources/bin/houdini` |
| Windows x64 | `meshy-dcc-houdini-windows-x64.zip` | `C:/Program Files/Side Effects Software/Houdini */bin/houdini.exe` |

Linux is not packaged. The adapter's Python code needs Python 3.8 or newer
(the bundled `meshy_dcc_core` is a `cp38-abi3` build).

## Agent quick path

```text
meshy-dcc install --dcc-type houdini --execute
```

With several Houdini versions installed, name one:
`--dcc-path <houdini executable or .app>`. The install:

1. downloads the platform zip, checks its SHA-256 and extracts it into the
   Meshy DCC adapters directory;
2. runs `bin/meshy-dcc-houdini install --dcc-path <houdini> --json`, which
   writes one Houdini package file, `meshy_dcc_houdini.json`, into that
   version's user preferences:
   - Windows: `$HOME/houdini<version>/packages`, where `$HOME` is the `HOME`
     variable when set and the Documents folder otherwise (Houdini's own rule);
   - macOS: `~/Library/Preferences/houdini/<version>/packages`;
   - `HOUDINI_USER_PREF_DIR` (with `__HVER__`) overrides both;
3. records the launch plan, so `meshy-dcc start-instance --dcc-type houdini`
   starts that Houdini.

The version comes from the executable's path (`Houdini21.0.440`,
`Houdini 21.0.440`, `Versions/21.0`). For an install whose path names no
version, set `MESHY_DCC_HOUDINI_VERSION=21.0` for the install.

## Manual path

Extract the zip somewhere it can stay, then register it:

```text
<extracted>/bin/meshy-dcc-houdini install --dcc-path <houdini executable> --json
```

On Windows the command is `bin\meshy-dcc-houdini.cmd`. Keep the extracted
directory in place while the package file points at it.

## Verify

Start Houdini (or `meshy-dcc start-instance --dcc-type houdini`). Once the UI
is ready, the console shows `Meshy DCC for Houdini is listening on ...` and
`meshy-dcc list` shows one live `houdini` instance. Read back with a
read-only tool, for example `houdini_scripting__get_session_info`.

## Upgrade

Close Houdini and rerun the install. The new build replaces the extracted
directory, and the package file is rewritten.

## Uninstall

Close Houdini, then:

```text
<extracted>/bin/meshy-dcc-houdini uninstall --dcc-path <houdini executable> --json
```

It deletes `meshy_dcc_houdini.json` only when it points at that extracted
directory (`removed`); a file from another copy is reported as `kept`.
Delete the extracted directory afterwards. Reinstalling first runs this same
uninstall.

## Troubleshooting

- Nothing starts: check that `<prefs>/packages/meshy_dcc_houdini.json` exists
  for the Houdini version you launch, and that `MESHY_DCC_HOUDINI_AUTOSTART`
  is not `0`.
- Windows with `HOME` set only in a terminal (Git Bash sets it): the install
  writes to `%HOME%/houdini<version>`, while Houdini launched from the Start
  menu reads the Documents folder. Install from the environment that launches
  Houdini, or set `HOUDINI_USER_PREF_DIR` for both.
- Background renders and cooks set `MESHY_DCC_BACKGROUND_RENDER=1` /
  `MESHY_DCC_BACKGROUND_COOK=1`; their hython processes never start another
  adapter.
- Headless `hython` does not run `uiready.py`; serve it in the foreground with
  `hython -m meshy_dcc_houdini`.

## Developer lifecycle (hython)

From a source checkout, the adapter can also be installed into Houdini's own
`hython` environment. This path predates the package above and is kept for
development; `meshy-dcc-houdini` here is the console script of that install.

```text
<hython> -m pip install -e <checkout> <meshy_dcc_core wheel>
meshy-dcc-houdini install --json --dry-run --dcc-path <houdini> --python <hython>
meshy-dcc-houdini install --json --yes --dcc-path <houdini> --python <hython>
meshy-dcc-houdini status --json --dcc-path <houdini> --python <hython>
meshy-dcc-houdini verify --json --dcc-path <houdini> --python <hython>
meshy-dcc-houdini upgrade --json --yes --dcc-path <houdini> --python <hython>
meshy-dcc-houdini uninstall --json --yes --dcc-path <houdini> --python <hython>
```

It writes a receipted `meshy_dcc_houdini.json` and startup hooks under the
versioned profile (the same file name as the package above, so only one of
the two is active). Its preflight runs `hython`, which needs a Houdini license
that allows it. When Houdini is not running, install succeeds, reports
`verify.directly_usable: false` and marks the verify step `pending`. Exits:
`0` success, `10` preflight, `20` acquire, `30` install or rollback, `40`
verify, `50` a loaded file that needs a Houdini restart.
