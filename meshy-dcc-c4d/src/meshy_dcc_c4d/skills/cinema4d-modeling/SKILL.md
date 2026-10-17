---
name: cinema4d-modeling
description: >-
  Create and transform typed Cinema 4D primitives, import geometry, export documents,
  and render images through an isolated c4dpy process. No arbitrary Python execution.
license: MIT
compatibility: "Cinema 4D R23+ with licensed c4dpy; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: c4d
    layer: domain
    version: "0.1.0"
    tags: "cinema4d,modeling,import,export,render"
    tools: tools.yaml
    depends: ["cinema4d-session", "dcc-diagnostics"]
---

# Cinema 4D modeling

Inspect the document before changing it. Use unique object names, save mutations to the
same `.c4d` document, and inspect or validate the durable result. Paths are restricted to
`MESHY_DCC_C4D_ALLOWED_ROOTS`; set `MESHY_DCC_C4D_C4DPY` when discovery cannot
locate the licensed `c4dpy` executable.
