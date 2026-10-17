from meshy_dcc_core.skill import run_main

from meshy_dcc_freecad.skill_tools import bridge_main

main = bridge_main("pocket_feature", "FreeCAD pocket feature created.")

if __name__ == "__main__":
    run_main(main)
