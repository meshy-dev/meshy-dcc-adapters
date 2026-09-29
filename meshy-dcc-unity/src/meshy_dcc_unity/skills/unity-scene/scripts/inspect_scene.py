from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host
from meshy_dcc_unity.server import publish_scene_snapshot


@skill_entry
def main(max_nodes: int = 1000, **_kwargs):
    result = call_host("scene.inspect", {"max_nodes": max_nodes})
    publish_scene_snapshot(result)
    return skill_success("Unity scene inspected.", **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
