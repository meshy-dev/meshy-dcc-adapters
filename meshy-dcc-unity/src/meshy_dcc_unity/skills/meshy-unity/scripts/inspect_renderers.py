from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host


@skill_entry
def main(max_findings=None, max_material_slots=None, **_kwargs):
    parameters = {}
    if max_findings is not None:
        parameters["max_findings"] = max_findings
    if max_material_slots is not None:
        parameters["max_material_slots"] = max_material_slots
    return skill_success("Unity renderers inspected.", **call_host("meshy.renderers.inspect", parameters))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
