# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_c4d`, the command is
  `meshy-dcc-c4d`, environment variables are `MESHY_DCC_C4D_*`, and the
  adapter registers only as dcc type `c4d`.
- Runs on `meshy_dcc_core` 0.2.x. The lifecycle commands record the
  `meshy-dcc-server` distribution only when it is installed; the Meshy package
  does not ship it.
