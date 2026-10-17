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

Start with `get_status`, then create or inspect a `.c4d` document. Every path must be
inside `MESHY_DCC_C4D_ALLOWED_ROOTS`; set `MESHY_DCC_C4D_C4DPY` when automatic
discovery cannot locate the licensed executable. Document writes use an atomic staged
file and are re-opened after mutation. Use `cinema4d-modeling` for object, interchange,
and rendering operations.

