# meshy-dcc-adapters

Host adapters for [Meshy DCC Core](https://github.com/meshy-dev/meshy-dcc-core):
each one lets an agent, through the `meshy-dcc` CLI and its local gateway,
work inside one desktop host. They are installed with `meshy-dcc install
<host>`, which downloads the adapter build the core catalog pins.

These are not the Meshy "Send To" / web bridge plugins, which carry Meshy
web-app results into a host and live elsewhere.

| Directory | Host | Version |
|---|---|---|
| [`meshy-dcc-blender/`](meshy-dcc-blender/) | Blender (extension) | 0.1.0 |
| [`meshy-dcc-unity/`](meshy-dcc-unity/) | Unity Editor (UPM package + Python sidecar) | 0.1.0 |
| [`meshy-dcc-godot/`](meshy-dcc-godot/) | Godot (editor plugin + Python sidecar) | 0.1.0 |
| [`meshy-dcc-unreal/`](meshy-dcc-unreal/) | Unreal Editor (plugin, Unreal's Python) | 0.1.0 |

Each directory is a self-contained project with its own README, CHANGELOG,
tests, packaging and version line, built against the `meshy_dcc_core` wheel
from meshy-dcc-core. Each began as a fork of an MIT-licensed project and has
fully diverged from it; its `LICENSE` and `NOTICE` carry the attribution.

## Releases

One adapter is released at a time, tagged `<host>-v<version>` (for example
`blender-v0.1.0`). A release publishes that adapter's builds for macOS Apple
Silicon and Windows x64 to the GitHub Release and to the Meshy CDN
(`meshy-dcc-core/adapters/<host>/v0-1-0/meshy-dcc-<host>-<macos-arm64|windows-x64>.zip`);
the core catalog then pins their URLs and SHA-256 digests.

To release: bump the adapter's `pyproject.toml` version and `CHANGELOG.md`,
create the GitHub Release `<host>-v<version>` (a draft is fine), then run the
`release` workflow from main with that tag and the meshy-dcc-core release
whose wheels to bundle. Both platforms are built on macOS by
`scripts/build_release.py`, which you can run locally the same way:

```sh
uv run --python 3.11 --no-project python scripts/build_release.py blender --core-wheel-dir <core wheels> --out out
```

The Release gets the zips under their CDN names plus `SHA256SUMS`.
