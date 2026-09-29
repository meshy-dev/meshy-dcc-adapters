from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(**_kwargs):
    return skill_success("Godot project inspected.", **call_host("project.inspect"))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
