r"""Start the meshy-dcc-3dsmax sidecar bridge from inside 3ds Max.

Run in MAXScript Listener:

    python.ExecuteFile @"C:\path\to\meshy-dcc-3dsmax\examples\start_sidecar_bridge.py"
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import meshy_dcc_core  # noqa: F401
    import meshy_dcc_server  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name not in {"meshy_dcc_core", "meshy_dcc_server"}:
        raise
    print(
        "{} is not installed in this 3ds Max Python. "
        "Run `just max-install-core-win` from the repo, then retry this command."
        .format(exc.name)
    )
    raise

from meshy_dcc_3dsmax.max_bootstrap import main  # noqa: E402

main()
