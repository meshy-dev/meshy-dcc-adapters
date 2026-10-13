from meshy_dcc_core.skill import skill_entry

from meshy_dcc_godot.capability_dispatch import dispatch


@skill_entry
def main(_action_name: str = "", **params):
    return dispatch(_action_name, params)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
