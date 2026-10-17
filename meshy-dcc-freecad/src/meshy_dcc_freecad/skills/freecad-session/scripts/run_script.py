from meshy_dcc_core.skill import run_main

from meshy_dcc_freecad.skill_tools import script_main

main = script_main("run_script", "FreeCAD script executed.")


if __name__ == "__main__":
    run_main(main)
