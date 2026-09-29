from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host


@skill_entry
def main(path, material_root=None, material_textures=None, **_kwargs):
    parameters = {"path": path}
    if material_root is not None:
        parameters["material_root"] = material_root
    if material_textures is not None:
        parameters["material_textures"] = material_textures
    return skill_success("Unity model instantiated.", **call_host("meshy.model.instantiate", parameters))


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
