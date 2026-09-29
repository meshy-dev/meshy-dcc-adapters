from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(node_path: str = "", path: str = "", **_kwargs):
    params = {"node_path": node_path} if node_path else {"path": path}
    return skill_success("Godot model inspected.", **call_host("meshy.inspect_model", params))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
