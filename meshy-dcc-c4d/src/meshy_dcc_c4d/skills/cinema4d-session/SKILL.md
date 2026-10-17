---
name: cinema4d-session
description: >-
  Discover licensed c4dpy and create, inspect, validate, or copy durable Cinema 4D
  documents through a bounded headless process. No arbitrary Python execution.
license: MIT
compatibility: "Cinema 4D R23+ with licensed c4dpy; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: c4d
    layer: domain
    version: "0.1.0"
    tags: "cinema4d,mcp,dcc,documents,automation"
    tools: tools.yaml
    depends: ["dcc-diagnostics"]
---

# Cinema 4D session

Start with `get_status`: it runs the licensed `c4dpy` once and reports the Cinema 4D,
API and Python versions. Then create or inspect a `.c4d` document. Every path must be
inside the folder the instance was started for (`MESHY_DCC_C4D_ALLOWED_ROOTS`). Each
call starts `c4dpy` and works on the file on disk, not on a scene open in the Cinema 4D
GUI. Document writes use an atomic staged file and are re-opened after mutation. Use
`cinema4d-modeling` for object, interchange, and rendering operations.
