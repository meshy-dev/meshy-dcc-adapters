from meshy_dcc_core.skill import run_main

from meshy_dcc_c4d.skill_tools import bridge_main

main = bridge_main("inspect_document", "Cinema 4D document inspected.")

if __name__ == "__main__":
    run_main(main)
