from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_godot.bridge import call_host


@skill_entry
def main(path: str, source: str, overwrite: bool = False, **_kwargs):
    result = call_host(
        "project.write_script", {"path": path, "source": source, "overwrite": overwrite}
    )
    return skill_success(f"Wrote Godot script {path}.", **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
