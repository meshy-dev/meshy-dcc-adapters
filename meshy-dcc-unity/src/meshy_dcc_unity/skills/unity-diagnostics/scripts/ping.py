from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host


@skill_entry
def main(**_kwargs):
    result = call_host("host.ping", {})
    return skill_success("Unity Editor main-thread dispatch is ready.", **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
