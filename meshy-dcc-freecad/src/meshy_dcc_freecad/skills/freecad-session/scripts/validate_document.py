from meshy_dcc_core.skill import run_main

from meshy_dcc_freecad.skill_tools import bridge_main

main = bridge_main("validate_document", "FreeCAD document validation finished.")

if __name__ == "__main__":
    run_main(main)
