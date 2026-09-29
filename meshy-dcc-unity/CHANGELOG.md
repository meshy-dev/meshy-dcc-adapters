# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter:
  - the Python package is `meshy_dcc_unity`, the UPM package is
    `ai.meshy.dcc`, and environment variables are `MESHY_DCC_UNITY_*`;
  - the sidecar runs on `meshy_dcc_core` 0.2.x;
  - the Editor bridge defaults to port 13852.
- `install --python` accepts a venv interpreter; it no longer follows the
  symlink out of the venv.
