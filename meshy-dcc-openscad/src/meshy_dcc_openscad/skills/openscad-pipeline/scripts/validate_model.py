from meshy_dcc_core.skill import run_main

from meshy_dcc_openscad.skill_tools import bridge_main

main = bridge_main("validate_model", "OpenSCAD model validation finished.")

if __name__ == "__main__":
    run_main(main)
