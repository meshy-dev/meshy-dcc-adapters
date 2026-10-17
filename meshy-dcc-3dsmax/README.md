# meshy-dcc-3dsmax

The Meshy DCC Core adapter for Autodesk 3ds Max (Windows only). It runs inside
3ds Max on the host's own Python (`pymxs`), registers the session with the
local `meshy-dcc` gateway, and exposes scene, import, material, render and save
tools that agents call through the `meshy-dcc` CLI.

Not verified on a real 3ds Max yet; experimental.

## License

MIT source; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
