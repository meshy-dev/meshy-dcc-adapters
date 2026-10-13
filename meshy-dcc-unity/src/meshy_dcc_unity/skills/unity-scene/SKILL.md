---
name: unity-scene
description: >-
  Domain skill — Inspect and edit the active Unity scene with typed, undoable
  GameObject operations. Use for hierarchy, object creation, transforms, and
  scene saves. Not for asset imports — use unity-project.
license: MIT
compatibility: "Unity 2018.4.25f1+ (.NET 4.x); meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: unity
    layer: domain
    version: "0.1.0"
    search-hint: "Unity scene hierarchy GameObject transform save Undo"
    tags: "unity,scene,gameobject,transform,game-development"
    tools: tools.yaml
    depends: "dcc-diagnostics"
---

# Unity Scene

Inspect the hierarchy immediately before using instance IDs. Treat every Unity instance ID as an
opaque, session-scoped value and return it unchanged; Unity 6000.5+ emits decimal strings while
older Editors retain integer output for compatibility. Both forms are accepted as input. Object
creation and transform edits register with Unity Undo.

Do not automatically retry a timed-out mutation. Inspect the project and scene first because the
Editor may have completed the original request near the timeout boundary.
