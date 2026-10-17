# meshy-dcc-maya

The Meshy DCC Core adapter for Autodesk Maya. It runs inside Maya as the
module `meshy_dcc_maya`: when Maya starts, the module's `userSetup.py` loads
the plug-in `meshy_dcc_maya_plugin`, which registers the Maya session with
the local `meshy-dcc` registry and serves 34 skills (275 tools: scene,
geometry and FBX/OBJ interchange, materials, rendering, rigging, animation
and more, plus `meshy-maya` for Meshy model handoff) to agents through the
`meshy-dcc` CLI.

Not verified on a real Maya yet; experimental. It is built for Maya 2025 and
2026 (Python 3.11) on macOS arm64 and Windows x64, and needs
`meshy-dcc-core>=0.2.0,<0.3.0`. Everything here is covered by unit tests
against stand-ins for `maya.cmds` only.

## With Meshy DCC

```sh
meshy-dcc install --dcc-type maya --execute
meshy-dcc start-instance --dcc-type maya --wait-ready --yes
```

The install downloads the package, checks its SHA-256, extracts it into the
Meshy DCC adapters folder and runs `bin/meshy-dcc-maya install --json`. That
writes one file, `meshy_dcc_maya.mod`, into the user's Maya modules folder,
pointing Maya at the extracted module. See [install.md](install.md) for where
that folder is, how to remove the adapter, and what each Maya session does.

## Build

```sh
python packaging/build_package.py --core-wheel <meshy_dcc_core wheel> \
    --platform macos-arm64 --output-dir dist
```

`--platform windows-x64` builds the Windows package on any machine. The core
wheel must match the platform.

## License

MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
