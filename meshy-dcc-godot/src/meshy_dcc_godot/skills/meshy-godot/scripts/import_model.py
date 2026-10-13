from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(path: str, name: str = "", **_kwargs):
    params = {"path": path, **({"name": name} if name else {})}
    return skill_success(
        "GLB instanced in the active scene; inspect the returned node before saving.",
        **call_host("meshy.import_model", params),
    )


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
