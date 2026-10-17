from meshy_dcc_core.skill import run_main

from meshy_dcc_freecad.skill_tools import snapshot_main

main = snapshot_main("restore_snapshot", "FreeCAD document restored from snapshot.")


if __name__ == "__main__":
    run_main(main)
