# Cursor Editor Integration Guide


> Vendor integration notes for `meshy-dcc-maya`. Moved here from the repo root so that
> [`AGENTS.md`](https://github.com/meshy-dev/meshy-dcc-maya/blob/main/AGENTS.md) stays the **only** agent contract file at the root.
> Anything not specific to this vendor belongs in `AGENTS.md`, not here.
> Cursor-specific integration notes for `meshy-dcc-maya`.
> For the full project map, see [AGENTS.md](https://github.com/meshy-dev/meshy-dcc-maya/blob/main/AGENTS.md).

---

## What This Project Does

`meshy-dcc-maya` embeds an MCP Streamable HTTP server directly inside Autodesk Maya. Cursor (via its MCP server support) can invoke Maya tools while you edit code, enabling a tight feedback loop between code changes and 3D scene state.

---

## Cursor Configuration

In Cursor Settings → MCP Servers, add:

```json
{
  "maya": {
    "url": "http://127.0.0.1:19765/mcp"
  }
}
```

For multi-instance gateway mode:
```json
{
  "maya": {
    "url": "http://127.0.0.1:19765/mcp"
  }
}
```

---

## Cursor-Specific Workflows

### 1. Skill Script Development (Edit → Test → Iterate)
The ideal Cursor workflow for `meshy-dcc-maya`:

1. **Edit** a skill script in `src/meshy_dcc_maya/skills/maya-my-feature/scripts/my_tool.py`.
2. **Save** — if hot-reload is enabled (`MESHY_DCC_MAYA_HOT_RELOAD=1`), the server picks up changes automatically.
3. **Test** — ask Cursor to call the tool: `"Run my_tool with radius=2"`.
4. **Verify** — `"Capture the viewport"` to see the result as a base64 PNG.

### 2. Inline Code Review for Skills
Paste a skill script into Cursor and ask:
> "Review this Maya skill script for thread safety. Does it need `affinity: main`?"

Cursor can cross-reference `tools.yaml` and the script content to validate the affinity declaration.

### 3. Refactoring Across Skills
Cursor's codebase-aware edits work well for bulk changes:
> "Update all skills that use `error_result(..., str(exc))` to use `maya_from_exception(exc, ...)` instead"

---

## Cursor-Specific Tips

- **Hot reload:** Set `MESHY_DCC_MAYA_HOT_RELOAD=1` before starting the server. Cursor edits to skill scripts are reflected immediately without restarting Maya.
- **Terminal integration:** Use Cursor's integrated terminal to run `python tools/lint_skill_affinity.py` before committing new skills.
- **Composability:** Cursor can generate multi-file skill packages. Create `SKILL.md`, `tools.yaml`, `groups.yaml`, and `scripts/*.py` in a single session.

---

## See Also

- [AGENTS.md](https://github.com/meshy-dev/meshy-dcc-maya/blob/main/AGENTS.md) — Shared agent navigation map; keep common guidance single-sourced there
- [llms.txt](https://github.com/meshy-dev/meshy-dcc-maya/blob/main/llms.txt) — One-page core reference
- [llms-full.txt](https://github.com/meshy-dev/meshy-dcc-maya/blob/main/llms-full.txt) — Exhaustive API reference
- [README.md](https://github.com/meshy-dev/meshy-dcc-maya/blob/main/README.md) — Human-facing installation and overview
