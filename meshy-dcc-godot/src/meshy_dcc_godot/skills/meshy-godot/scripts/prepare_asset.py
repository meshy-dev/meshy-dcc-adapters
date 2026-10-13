from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(path: str, **_kwargs):
    return skill_success(
        "Godot asked to scan the GLB; poll session with asset_path until asset_ready.",
        **call_host("meshy.prepare_asset", {"path": path}),
    )


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
