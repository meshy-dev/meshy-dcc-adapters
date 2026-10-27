---
name: blender-scene
description: "Blender scene management — create, open, save, list and inspect scene objects"
license: "MIT"
allowed-tools: ["Bash", "Read"]
metadata:
  meshy-dcc:
    dcc: blender
    layer: domain
    stage: bootstrap
    version: "1.0.0"
    tags: [blender, scene, hierarchy]
    search-hint: "new scene, open, save, list objects, hierarchy, scene info, session, diagnostics"
    search-aliases: [scene summary, session info, get scene, new blend file, open blend, save blend, inspect scene, list objects]
    intent: "Inspect and manage Blender scene lifecycle — create, open, save scenes, list objects, and retrieve session diagnostics."
    recall-context:
      app_type: blender
      domain: scene
      workflow_stage: bootstrap
      task_category: query
    preconditions:
      - type: software
        name: blender
        version: ">=4.0"
    side-effects:
      creates: true
      modifies: true
      file_output: true
      targets: [scene, file:blend]
    produces: [scene_info, session_info, file:blend, object_list]
    requires: []
    tools: tools.yaml
---

# blender-scene

Blender scene management skill — create, open, save and inspect scenes.

## Verified saves

`save_scene` uses Save As when `filepath` is given and saves the current file
when it is omitted. It reports success only when Blender returns `FINISHED` and
the path Blender then reports for the scene is a regular, nonempty file written
by this call: a file that was already there does not count. `context.filepath`
is that verified path (Blender appends `.blend` to an extensionless one) and
`postcondition.verified` is `true`. This does not prove the content is intact;
reopen the file for that.

When the operator or the readback fails, the result is an error with
`mutation_applied: null`: the file on disk may or may not have changed. The
save is not retried, rolled back or deleted. Inspect the path before going on.
