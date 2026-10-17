from meshy_dcc_core.skill import run_main

from meshy_dcc_c4d.skill_tools import bridge_main

main = bridge_main("add_primitive", "Cinema 4D primitive added.")

if __name__ == "__main__":
    run_main(main)
