---
name: zbrush-file
description: >-
  Domain skill — save the open ZBrush project (.zpr) or the active tool (.ztl)
  to an exact path, and open a .zpr project. Use to keep work before stopping
  ZBrush and to reopen it. Not for mesh export — use zbrush-interchange.
license: MIT
compatibility: "ZBrush 2026.1+; meshy-dcc-core 0.2.x"
allowed-tools: Bash Read Write
metadata:
  meshy-dcc:
    dcc: zbrush
    layer: domain
    stage: pipeline
    version: "1.0.0"
    tags: [zbrush, save, open, zpr, ztl, project]
    search-hint: "save project, save zpr, save tool, save ztl, open project, reopen"
    tools: tools.yaml
---

# zbrush-file

Saves through `set_next_filename` + `File:Save As` (project) or
`Tool:Save As` (active tool with all its subtools), and opens through
`File:Open`. A save checks that ZBrush wrote a non-empty file at the path;
an existing file is replaced only with `overwrite: true`, and is put back
if the save fails. Opening a project replaces what ZBrush has open without
asking, so save first.

ZBrush cannot report unsaved changes. Treat everything since the last save
as unsaved.

Not verified on a real ZBrush yet.
