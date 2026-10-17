from meshy_dcc_core.skill import run_main

from meshy_dcc_material_maker.skill_tools import bridge_main

main = bridge_main("edit_graph", "Material Maker graph edited and saved.")

if __name__ == "__main__":
    run_main(main)
