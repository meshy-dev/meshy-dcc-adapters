# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from (dcc-mcp-substance3d-painter 0.6.3).

- Meshy-owned adapter: the Python package is `meshy_dcc_substance3d_painter`,
  the dcc type `substance3d_painter`, environment variables
  `MESHY_DCC_SUBSTANCE3D_PAINTER_*`; it runs on `meshy_dcc_core` 0.2.x.
- `packaging/build_package.py --platform macos-arm64|windows-x64` builds the
  Meshy DCC package on any machine: this adapter and `meshy_dcc_core` in
  `plugin/python/`, a pinned python-build-standalone CPython 3.11.15 (its
  SHA-256 checked) for the installer, and `bin/meshy-dcc-substance3d-painter`
  (`.cmd` on Windows). The package leaves out `direct_url.json`, which would
  record local build paths.
- New installer (`meshy-dcc-substance3d-painter install | uninstall |
  status`): writes one startup loader into the user's Painter profile and
  removes it again; it never overwrites or deletes a file it did not write.
  It replaces the upstream installer, which loaded the adapter from a
  separately installed Python environment.
- Safe stop for instances launched by `meshy-dcc start-instance`: refuses
  while the open project needs saving, or when Painter cannot tell, unless the
  caller agreed to discard unsaved work.
- The Painter version reported by the server and `ping` now comes from
  `substance_painter.application.version()`; upstream read a module attribute
  that does not exist and always reported a placeholder.
- `create_project` and `reload_mesh` document glTF (`.gltf`, `.glb`) meshes,
  which Painter imports.
- Not verified on a real Painter yet.
