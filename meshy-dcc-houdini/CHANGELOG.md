# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from. Not verified on a real Houdini yet.

- Meshy-owned adapter:
  - Python package and environment variables are renamed to
    `meshy_dcc_houdini` / `MESHY_DCC_HOUDINI_*`;
  - the adapter builds against `meshy_dcc_core` 0.2.x.
- `packaging/build_package.py` builds the Meshy DCC package for macOS arm64
  and Windows x64: the adapter and `meshy_dcc_core` in `lib/`, startup files
  in `houdini/`, and a pinned CPython for the registration step. The
  registration (`bin/meshy-dcc-houdini install|uninstall --dcc-path`) writes
  or removes one Houdini package file in the user preferences.
- Startup runs from `pythonX.Ylibs/uiready.py` only, in interactive sessions.
  The quickinstall's `123.py` / `456.py` hooks are gone: Houdini runs only the
  first of each on its path, so they hid a user's own scripts.
- A Houdini launched by `meshy-dcc start-instance` advertises a safe stop that
  refuses while the scene has unsaved changes unless the request carries
  `discard_unsaved`.
- The live e2e smoke runner moves to `tools/run_houdini_e2e.py`.
