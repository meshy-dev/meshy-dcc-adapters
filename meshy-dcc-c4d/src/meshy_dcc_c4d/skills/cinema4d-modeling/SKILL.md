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
the folder the instance was started for (`MESHY_DCC_C4D_ALLOWED_ROOTS`). A document that
is also open in the Cinema 4D GUI does not see these changes until it is reopened there,
and saving it from the GUI overwrites them.
