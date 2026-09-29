from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host


@skill_entry
def main(path, **_kwargs):
    return skill_success("Unity scene opened.", **call_host("meshy.scene.open", {"path": path}))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
