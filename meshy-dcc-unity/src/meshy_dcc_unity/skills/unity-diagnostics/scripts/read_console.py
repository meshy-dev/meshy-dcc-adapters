from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_unity.bridge import call_host


@skill_entry
def main(limit: int = 100, severity: str = "all", **_kwargs):
    result = call_host("editor.read_console", {"limit": limit, "severity": severity})
    count = len(result.get("entries", []))
    return skill_success(f"Read {count} captured Unity Console entries.", **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
