"""Auto-start meshy-dcc-zbrush when ZBrush loads this plugin directory.

Install by copying the whole ``bridge/plugin/meshy_dcc_zbrush`` folder into a
``ZBRUSH_PLUGIN_PATH`` entry or by adding this repo's ``src`` tree to
``PYTHONPATH``.

Registers a top-level Meshy DCC palette (PIP-2905):
  meshy_dcc_copy_instance_id()  — Copy instance UUID to clipboard
  meshy_dcc_show_server_info()  — Show server status dialog
  meshy_dcc_show_about()        — Show About Meshy DCC dialog
"""

from __future__ import annotations

import os
from typing import Any


def _autostart_enabled() -> bool:
    raw = os.environ.get("MESHY_DCC_ZBRUSH_AUTOSTART", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


# ── Unified menu actions (PIP-2905) ────────────────────────────────────────


def meshy_dcc_copy_instance_id() -> None:
    """Copy the Meshy DCC instance UUID to the system clipboard."""
    try:
        from meshy_dcc_zbrush._menu import copy_instance_id

        copy_instance_id()
    except ImportError:
        print("meshy-dcc-zbrush is not installed — cannot copy instance ID")  # noqa: T201


def meshy_dcc_show_server_info() -> None:
    """Show Meshy DCC server information."""
    try:
        from meshy_dcc_zbrush._menu import show_server_info

        show_server_info()
    except ImportError:
        print("meshy-dcc-zbrush is not installed — cannot show server info")  # noqa: T201


def meshy_dcc_show_about() -> None:
    """Show About Meshy DCC dialog."""
    try:
        from meshy_dcc_zbrush._menu import show_about

        show_about()
    except ImportError:
        print("meshy-dcc-zbrush is not installed — cannot show about")  # noqa: T201


def _on_copy_instance_id(_sender: str) -> None:
    meshy_dcc_copy_instance_id()


def _on_show_server_info(_sender: str) -> None:
    meshy_dcc_show_server_info()


def _on_show_about(_sender: str) -> None:
    meshy_dcc_show_about()


def install_menu(zbc: Any = None) -> bool:
    """Install the top-level Meshy DCC palette through the official SDK."""
    if zbc is None:
        import zbrush.commands as zbc  # noqa: PLC0415

    if not zbc.exists("Meshy DCC") and not zbc.add_palette("Meshy DCC", docking_bar=1):
        return False
    actions = (
        ("Copy Instance ID", "Copy the Meshy DCC instance UUID to the clipboard.", _on_copy_instance_id),
        ("Server Info", "Show Meshy DCC server and runtime information.", _on_show_server_info),
        ("About Meshy DCC", "Show adapter and ZBrush version information.", _on_show_about),
    )
    for label, info, callback in actions:
        item_path = f"Meshy DCC:{label}"
        if not zbc.exists(item_path) and not zbc.add_button(item_path, info, callback):
            return False
    return True


# ── Autostart ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not install_menu():
        print("meshy-dcc-zbrush — failed to register Meshy DCC palette")  # noqa: T201
    if _autostart_enabled():
        import meshy_dcc_zbrush  # noqa: PLC0415

        meshy_dcc_zbrush.start_server(mode="embedded")
