# meshy-dcc-material-maker

The Meshy DCC Core adapter for [Material Maker](https://www.materialmaker.org),
the open-source procedural material editor. An agent builds and edits
Material Maker graphs (`.ptex`) in a project folder and renders them, through
Material Maker's own command-line exporter, into PBR texture sets and engine
materials for Blender, Godot, Unity, Unreal or glTF: tileable materials for
Meshy models, or normal and height maps derived from a Meshy texture.

Targets Material Maker 1.7 and later. Verified with Material Maker 1.7 on
macOS arm64: install, `meshy-dcc start-instance`, graph creation and editing,
export with readback, save and reopen, and safe stop. The Windows x64 package
is built the same way and has not run on a real host yet.

## How it works

Material Maker has no plug-in or scripting interface, so the adapter is a
standalone sidecar with its own Python. Each instance serves one project
folder:

- graphs are JSON files, which the adapter reads and edits itself, checking
  node types, parameters and ports against the node library of the Material
  Maker it was set up with;
- an export runs Material Maker's documented
  `--export-material --target <profile> --output-dir <dir>` on the saved file.
  Material Maker briefly opens a 1x1 window and takes focus while it renders
  (`--headless` crashes Material Maker 1.7 on macOS, so it is not used); the
  textures come out at 2048x2048.

No tool reads or writes outside the project folder. Graphs that would reach
the camera (`webcam`), download nodes from materialmaker.org (`website:`) or
write outside the export folder are refused.

## With Meshy DCC

`packaging/build_package.py` builds the package: a relocatable CPython 3.11
with `meshy_dcc_core` and this adapter, plus `bin/meshy-dcc-material-maker-sidecar`.

```bash
meshy-dcc install --dcc-type material-maker --project /path/to/materials --execute
meshy-dcc start-instance --dcc-type material-maker --project /path/to/materials --wait-ready --yes
meshy-dcc load-skill material-maker-materials --dcc-type material-maker
```

Install extracts the package and runs its `install-project` verb, which
writes `.meshy-dcc/` into the folder: the start-instance launch plan, the
Material Maker executable to use, and a receipt (the directory ignores itself
for version control). Material Maker is found through `--dcc-path`, or in
`/Applications` and `~/Applications` on macOS. Material Maker itself is never
installed or changed.

The `material-maker-materials` skill has `get_status`, `create_material`,
`get_graph`, `edit_graph`, `list_node_types`, `inspect_project`,
`validate_project`, `export_material` and `open_in_material_maker`. Every edit
is saved at once, so an instance never has unsaved work and stops on request.

The edits go to the files, not to an open Material Maker window: Material
Maker does not reload a graph changed on disk, and saving there overwrites
the agent's change. The skill has agents ask the user to close a graph before
editing it, and `open_in_material_maker` opens the result in a new Material
Maker window for the user afterwards.

See [Installation](install.md) for the package's own verbs and diagnostics.

## Development

```bash
python -m pip install --no-deps <meshy_dcc_core wheel>
python -m pip install --no-deps -e .
python -m pip install pytest pytest-xdist pyyaml "jsonschema>=4.18"
PYTHONPATH=src:. python -m pytest tests -n 2
python tools/lint_skills.py
python packaging/build_package.py --core-wheel <wheel> --platform macos-arm64 --output-dir dist
```

The tests use synthetic node libraries and a stand-in executable.
`tests/live_material_maker_smoke.py` drives a real Material Maker
(`MESHY_DCC_MATERIAL_MAKER_EXECUTABLE`, `MESHY_DCC_MATERIAL_MAKER_SAMPLE`); run
it by hand with `MESHY_DCC_GATEWAY_PORT` set to a free port.
