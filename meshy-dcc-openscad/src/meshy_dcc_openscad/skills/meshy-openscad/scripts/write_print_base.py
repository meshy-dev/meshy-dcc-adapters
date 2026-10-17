from meshy_dcc_core.skill import run_main, skill_entry, skill_success

from meshy_dcc_openscad.print_base import write_print_base


@skill_entry
def main(**kwargs):
    result = write_print_base(**kwargs)
    checks = result.pop("verified")
    return skill_success(
        "Print-base SCAD source written and verified.",
        verified=True,
        verification_checks=checks,
        **result,
    )


if __name__ == "__main__":
    run_main(main)
