from meshy_dcc_core.skill import skill_entry

from meshy_dcc_unity.bridge import call_host
from meshy_dcc_unity.job_result import job_state_result


@skill_entry
def main(request_id: str, artifact_kind: str, **_kwargs):
    result = call_host(
        "project.build_android_player",
        {"request_id": request_id, "artifact_kind": artifact_kind},
    )
    return job_state_result("Unity Android player build", result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
