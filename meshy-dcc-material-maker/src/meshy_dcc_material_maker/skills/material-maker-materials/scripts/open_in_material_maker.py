from meshy_dcc_core.skill import run_main

from meshy_dcc_material_maker.skill_tools import bridge_main

main = bridge_main("open_in_material_maker", "Material Maker opened the graph for the user.")

if __name__ == "__main__":
    run_main(main)
