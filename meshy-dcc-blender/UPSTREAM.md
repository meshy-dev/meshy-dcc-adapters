# Upstream source

meshy-dcc-blender is the Meshy DCC Core adapter for Blender. It is built from
the source of [dcc-mcp-blender](https://github.com/dcc-mcp/dcc-mcp-blender)
(MIT) and does not carry upstream git history or GitHub workflows.

| Item | Value |
|---|---|
| Imported release | `v0.2.11` |
| Upstream commit | `cbcf6b058797b99db877095a1be658836d5e948c` |
| License | MIT source, upstream `LICENSE` retained unchanged |

Internal names (`dcc_mcp_blender`, `DCC_MCP_BLENDER_*`) stay as upstream has
them, so upstream patches still apply. The packaged extension bundles the
`dcc_mcp_core` wheel built from meshy-dcc-core:

```sh
python packaging/assemble_zip.py --platform macos --core-wheel <meshy-dcc-core wheel> --output-dir dist_addon
```

The assembled Blender extension archive is distributed as GPL-3.0-or-later,
as upstream does for Blender Extensions. Review this before any public release.

## Taking an upstream fix

Upstream changes arrive as patches, not merges:

```sh
git -C <upstream-clone> diff v0.2.11 <newer-tag> -- <paths> > upstream.patch
git apply -3 upstream.patch
```
