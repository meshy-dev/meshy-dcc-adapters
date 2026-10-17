# Install the Meshy DCC Material Maker adapter

The adapter never installs, updates or changes Material Maker itself. It
needs Material Maker 1.7.0 or newer from the official release
(<https://github.com/RodZill4/material-maker/releases>), on macOS or Windows.

## With meshy-dcc (the normal path)

```bash
meshy-dcc install --dcc-type material-maker --project /path/to/materials --execute
```

The catalog pins the package for the platform (`macos-arm64`,
`windows-x86_64`) by URL and SHA-256. `meshy-dcc` extracts it and runs, from
the package:

```text
meshy-dcc-material-maker install-project <folder> --dcc-path <Material Maker> --sidecar <package>/bin/meshy-dcc-material-maker-sidecar --yes --json
```

Pass `--dcc-path` to `meshy-dcc install` when Material Maker is not in a usual
place (`/Applications/Material Maker.app` on macOS; on Windows, where the zip
was extracted). A macOS `.app` path is accepted.

`install-project` writes only `<folder>/.meshy-dcc/`:

| File | Content |
| --- | --- |
| `launch-plan.json` | what `meshy-dcc start-instance` runs: the sidecar, bound to the folder |
| `material-maker.json` | the Material Maker executable the tools run |
| `.gitignore` | `*`, so the directory stays out of version control |
| `receipts/material-maker.json` | the SHA-256 of each file above |

Without `--yes` it reports the plan and writes nothing. Running it again with
the same settings changes nothing. It refuses a folder whose `.meshy-dcc/`
files another adapter wrote (one launch plan per folder): use a separate
folder for materials.

```text
meshy-dcc-material-maker uninstall-project <folder> --yes --json
```

removes the files whose content still matches the receipt and keeps any that
changed. Graphs and exports in the folder are never touched.

## Running the sidecar by hand

```text
meshy-dcc-material-maker serve --project <folder>
```

`MESHY_DCC_MATERIAL_MAKER_EXECUTABLE` overrides the recorded executable, and
`MESHY_DCC_MATERIAL_MAKER_VERSION` the version read from the macOS bundle.
Limits: `MESHY_DCC_MATERIAL_MAKER_MAX_PROJECT_BYTES`, `_MAX_NODES`,
`_MAX_CONNECTIONS`, `_MAX_EXPORT_FILES`, `_MAX_EXPORT_BYTES`,
`_MAX_TIMEOUT_SECS`.

## Diagnostics

The package also keeps the original adapter's Install SOP verbs, which check a
Material Maker with a real export of a `.ptex` you choose:

```text
meshy-dcc-material-maker doctor --json --dcc-path <Material Maker> --material-maker-version 1.7.0 --probe-project <file.ptex>
```

`install`, `upgrade` and `uninstall` (`--dry-run`, then `--yes`; `--execute`
is an alias) manage a separate configuration root
(`--install-root`, default `<user data>/meshy-dcc/adapters/material-maker`),
and `status` / `verify` check it. `--python` must name the interpreter running
the command. Exits: `0` ok, `10` preflight, `30` install, `40` verify.
`meshy-dcc` does not use this root.
