from meshy_dcc_core.skill import run_main

from meshy_dcc_c4d.skill_tools import bridge_main

main = bridge_main("import_geometry", "Geometry imported into Cinema 4D.")

if __name__ == "__main__":
    run_main(main)
