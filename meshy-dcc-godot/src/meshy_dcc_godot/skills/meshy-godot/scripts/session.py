from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(asset_path: str = "", **_kwargs):
    params = {"asset_path": asset_path} if asset_path else {}
    return skill_success("Godot session inspected.", **call_host("meshy.session", params))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
