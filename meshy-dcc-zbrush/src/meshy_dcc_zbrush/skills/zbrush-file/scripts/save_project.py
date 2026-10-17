"""Save the open project to a .zpr file through the ZBrush bridge."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_zbrush.api import get_bridge, with_zbrush, zb_success


@skill_entry
@with_zbrush
def save_project(path: str, overwrite: bool = False, **kwargs) -> dict:
    payload = get_bridge().call("save_file", kind="project", output_path=path, overwrite=overwrite)
    if isinstance(payload, dict) and payload.get("success") is False:
        return payload
    return zb_success(f"Saved the ZBrush project to {payload['path']}", **payload)


def main(**kwargs) -> dict:
    return save_project(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
