---
name: meshy-roblox
description: >-
  Domain skill — Put a Meshy GLB from disk into the open Roblox Studio place
  as a Model of MeshParts with a PBR SurfaceAppearance, and read it back.
  Studio cannot import a file without a dialog, so the sidecar decodes the GLB
  and the plugin rebuilds it; the result lives in this Studio session unless
  the user agrees to upload it to their Roblox account.
license: MIT
compatibility: "Roblox Studio with the Meshy DCC plugin; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: roblox
    layer: domain
    version: "0.1.0"
    search-hint: "Roblox Studio import GLB Meshy model MeshPart EditableMesh SurfaceAppearance texture PBR"
    tags: "roblox,meshy,import,glb,meshpart,pbr,handoff"
    tools: tools.yaml
    depends: "roblox-scene"
---

# Meshy model into Roblox Studio

1. `import_model` takes an absolute path to a self-contained `.glb` (textures
   embedded, as Meshy's GLB download is). It builds a Model named `name`
   (default: the file name) under `parent` (default `Workspace`), with the GLB
   origin at `position` (studs, default `[0, 0, 0]`). glTF metres become studs
   (`scale` 3.571 studs per metre by default). Meshes above 20,000 triangles
   are split into several MeshParts. Base color, normal, metalness and
   roughness maps go into a SurfaceAppearance, downscaled to at most 1024 px.
   It is one undo step. Never repeat it when the outcome is unknown; read the
   place instead.
2. `inspect_model` reads back a Model or MeshPart by path: MeshParts with
   vertex and triangle counts, size, position, mesh source and which texture
   maps are bound, plus the model's bounds and pivot.

Persistence: by default the meshes and images exist only in this Studio
session (`persistent: false`); Roblox does not save editable meshes with the
place, so they are gone after the place is closed and reopened. With
`publish: true` the plugin first uploads each mesh and image to the
logged-in Studio user's Roblox inventory (no prompt, subject to Roblox
moderation) and builds the model from those assets, which saves with the
place (`persistent: true`, `uploaded` lists the asset ids). Upload only after
the user agreed to it for this model. Uploads that finished stay in the
inventory even if a later step fails.

If the texture looks mirrored vertically, re-import with `flip_v: true` under
a new name and delete the first copy. Meshy models face +Z; Studio's default
camera looks toward -Z, so it may see the back. Saving the place is the
user's action in Studio.
