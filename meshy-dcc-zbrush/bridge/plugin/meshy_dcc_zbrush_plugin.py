"""ZBrush Python plugin entry point for embedded meshy-dcc-zbrush mode."""

from __future__ import annotations

import json
import os
import time


def _capture_bootstrap_error(stage: str, error: BaseException) -> None:
    configured = os.environ.get("MESHY_DCC_ZBRUSH_BOOTSTRAP_ERRORS", "").strip()
    default_root = os.path.dirname(os.path.abspath(__file__))
    path = configured or os.path.join(default_root, ".meshy-dcc", "bootstrap-errors.jsonl")
    payload = {
        "timestamp": time.time(),
        "stage": stage,
        "reason": str(error),
        "exception_type": type(error).__name__,
    }
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True) + "\n")
    except BaseException:
        pass


def _autostart_enabled() -> bool:
    raw = os.environ.get("MESHY_DCC_ZBRUSH_AUTOSTART", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


if __name__ == "__main__":
    try:
        identity_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "meshy_dcc_zbrush_install_identity.json",
        )
        if os.path.isfile(identity_path):
            os.environ["MESHY_DCC_ZBRUSH_INSTALL_IDENTITY"] = identity_path
        import meshy_dcc_zbrush

        if not meshy_dcc_zbrush.install_menu():
            print("meshy-dcc-zbrush — failed to register Meshy DCC palette")  # noqa: T201
        if _autostart_enabled():
            meshy_dcc_zbrush.start_server(mode="embedded")
    except BaseException as exc:
        _capture_bootstrap_error("embedded_bootstrap", exc)
        raise
