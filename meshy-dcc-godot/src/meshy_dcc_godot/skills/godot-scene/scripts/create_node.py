from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(type: str, name: str, parent_path: str = "", **_kwargs):
    result = call_host(
        "scene.create_node", {"type": type, "name": name, "parent_path": parent_path}
    )
    return skill_success(f"Created Godot node {name}.", **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
