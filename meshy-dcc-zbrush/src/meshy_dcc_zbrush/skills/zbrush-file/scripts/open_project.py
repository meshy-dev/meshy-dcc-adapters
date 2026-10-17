"""Open a .zpr project through the ZBrush bridge and read back what it loaded."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_zbrush.api import get_bridge, with_zbrush, zb_success


@skill_entry
@with_zbrush
def open_project(path: str, **kwargs) -> dict:
    payload = get_bridge().call("open_project", path=path)
    if isinstance(payload, dict) and payload.get("success") is False:
        return payload
    return zb_success(f"Opened the ZBrush project {payload['path']}", **payload)


def main(**kwargs) -> dict:
    return open_project(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
