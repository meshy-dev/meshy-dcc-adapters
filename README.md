# meshy-dcc-adapters

Connectors for [Meshy DCC Core](https://github.com/meshy-dev/meshy-dcc-core):
each one lets an agent, through the `meshy-dcc` CLI and its local gateway, work
inside one app. Install them with `meshy-dcc install --dcc-type <app>` or from
`meshy-dcc ui`; you do not need to build them yourself.

| Directory | App | Versions |
|---|---|---|
| [`meshy-dcc-blender/`](meshy-dcc-blender/) | Blender | 4.5 – 5.2 |
| [`meshy-dcc-unity/`](meshy-dcc-unity/) | Unity | 2018.4 – 6000.5 |
| [`meshy-dcc-godot/`](meshy-dcc-godot/) | Godot | 4.4 – 4.7 |
| [`meshy-dcc-unreal/`](meshy-dcc-unreal/) | Unreal Engine | 5.0 – 5.8 |
| [`meshy-dcc-maya/`](meshy-dcc-maya/) | Maya | 2023 – 2027 |
| [`meshy-dcc-3dsmax/`](meshy-dcc-3dsmax/) | 3ds Max (Windows) | 2023 – 2027 |
| [`meshy-dcc-houdini/`](meshy-dcc-houdini/) | Houdini | 20.5 – 22.0 |
| [`meshy-dcc-substance3d-painter/`](meshy-dcc-substance3d-painter/) | Substance 3D Painter | 10.0 – 12.1 |
| [`meshy-dcc-zbrush/`](meshy-dcc-zbrush/) | ZBrush | 2026.1 – 2026.2 |
| [`meshy-dcc-roblox/`](meshy-dcc-roblox/) | Roblox Studio | current release |
| [`meshy-dcc-freecad/`](meshy-dcc-freecad/) | FreeCAD | 1.0 – 1.1 |
| [`meshy-dcc-openscad/`](meshy-dcc-openscad/) | OpenSCAD | 2021.01; 2026.09 – 2026.10 snapshots |
| [`meshy-dcc-material-maker/`](meshy-dcc-material-maker/) | Material Maker | 1.7 |

On macOS (Apple Silicon) and Windows x64. `meshy-dcc-c4d/` (Cinema 4D) is not
released yet.

Each directory is a self-contained project with its own README, CHANGELOG,
tests, packaging and version, built against the `meshy_dcc_core` wheel from
meshy-dcc-core. Most began as a fork of an MIT-licensed project and have fully
diverged from it; their `LICENSE` and `NOTICE` carry the attribution.

## Releases

Each connector is released on its own, tagged `<app>-v<version>` (for example
`blender-v0.1.0`). A release publishes the macOS and Windows builds to the
GitHub Release and the Meshy CDN; the Meshy DCC Core install catalog then pins
their URLs and SHA-256 digests.

To release: bump the connector's `pyproject.toml` version and `CHANGELOG.md`,
push the tag `<app>-v<version>` and create its GitHub Release (a draft is
fine), then run the `release` workflow from main with that tag and the
meshy-dcc-core release whose wheels to bundle. Both platforms build on macOS
with `scripts/build_release.py`, which runs the same way locally:

```sh
uv run --python 3.11 --no-project python scripts/build_release.py blender --core-wheel-dir <core wheels> --out out
```

The CPython and PyPI packages a build takes are pinned in `build_release.py`,
so a tag always rebuilds with the same contents.
