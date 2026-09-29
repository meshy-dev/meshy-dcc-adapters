from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host


@skill_entry
def main(instance_id, **_kwargs):
    return skill_success("Unity object inspected.", **call_host("meshy.object.inspect", {"instance_id": instance_id}))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
