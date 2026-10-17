"""Keep test servers' logs, job databases and skill folders out of the real home."""

import os
import tempfile

_HOME = tempfile.mkdtemp(prefix="meshy-dcc-c4d-tests-")
os.environ["HOME"] = _HOME
os.environ["USERPROFILE"] = _HOME
os.environ["MESHY_DCC_LOG_DIR"] = os.path.join(_HOME, "log")
