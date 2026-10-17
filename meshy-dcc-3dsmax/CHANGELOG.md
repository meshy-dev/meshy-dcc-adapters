# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_3dsmax`, environment
  variables are `MESHY_DCC_3DSMAX_*`, and it runs on `meshy_dcc_core` 0.2.x.
- The 3ds Max menu and its CUI ids use Meshy's own ids (`0x4D455348`), so they
  never collide with another adapter's menu.
- Removed as leftovers of the original project: release-please and renovate
  configuration, `llms.txt` / `llms-full.txt`, the documentation site, images
  and branding, the CI release-workflow scripts and the tests that read the
  GitHub workflows, and the GitHub release-asset uploader.
