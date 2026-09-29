from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(title: str = "Meshy DCC Roguelike", **_kwargs):
    result = call_host("roguelike.create_prototype", {"title": title})
    return skill_success("Created a playable Godot 2D roguelike prototype.", **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
