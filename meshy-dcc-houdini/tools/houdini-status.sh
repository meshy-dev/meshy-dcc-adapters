#!/usr/bin/env sh
set -eu
if [ -z "${HOUDINI_PYTHON:-}" ]; then
  echo "Set HOUDINI_PYTHON to Houdini's python executable"
  exit 1
fi
SITE="$("$HOUDINI_PYTHON" -c 'import site; print(site.getsitepackages()[0])')"
TARGET="$SITE/meshy_dcc_houdini"
if [ -L "$TARGET" ] || [ -d "$TARGET" ]; then
  echo "Linked: $TARGET -> $(readlink "$TARGET" 2>/dev/null || echo '(directory)')"
else
  echo "Not linked: $TARGET"
fi
"$HOUDINI_PYTHON" -c "import meshy_dcc_houdini; print('import OK', meshy_dcc_houdini.__version__)" 2>/dev/null || echo "import failed"
