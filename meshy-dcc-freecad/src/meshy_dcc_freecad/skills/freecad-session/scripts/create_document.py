from meshy_dcc_core.skill import run_main

from meshy_dcc_freecad.skill_tools import bridge_main

main = bridge_main("create_document", "FreeCAD document created.")

if __name__ == "__main__":
    run_main(main)
