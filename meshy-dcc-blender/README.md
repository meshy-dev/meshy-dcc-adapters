# meshy-dcc-blender

The Meshy DCC Core adapter for Blender 4.5+. It runs inside Blender as the
extension `meshy_dcc_blender` ("Meshy DCC"). It registers the Blender session
with the local `meshy-dcc` registry and exposes scene, import, material,
render and save tools that agents call through the `meshy-dcc` CLI.

Verified on Blender 5.0.1, macOS arm64. The checks covered install through
`meshy-dcc install`, start-instance, GLB import with readback, save, and
consent-gated stop.

## Build

The extension bundles the `meshy_dcc_core` wheel built from meshy-dcc-core:

```sh
python packaging/assemble_zip.py --platform macos --core-wheel <meshy_dcc_core wheel> --output-dir dist_addon
```

The assembled Blender extension archive is distributed as GPL-3.0-or-later,
as Blender Extensions require. Review this before any public release.

## License

MIT source; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
