from meshy_dcc_core.skill import run_main

from meshy_dcc_material_maker.skill_tools import bridge_main

main = bridge_main("validate_project", "Material Maker project validated.")

if __name__ == "__main__":
    run_main(main)
