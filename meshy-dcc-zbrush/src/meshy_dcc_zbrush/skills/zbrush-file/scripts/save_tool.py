"""Save the active tool to a .ztl file through the ZBrush bridge."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_zbrush.api import get_bridge, with_zbrush, zb_success


@skill_entry
@with_zbrush
def save_tool(path: str, overwrite: bool = False, **kwargs) -> dict:
    payload = get_bridge().call("save_file", kind="tool", output_path=path, overwrite=overwrite)
    if isinstance(payload, dict) and payload.get("success") is False:
        return payload
    return zb_success(f"Saved the active ZBrush tool to {payload['path']}", **payload)


def main(**kwargs) -> dict:
    return save_tool(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
