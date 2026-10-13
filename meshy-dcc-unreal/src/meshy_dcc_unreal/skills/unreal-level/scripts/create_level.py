"""Create and save a new Unreal Engine level."""

from __future__ import annotations

from meshy_dcc_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def create_level(level_path: str, template_path: str = "", **_kwargs) -> dict:
    if not level_path.startswith("/Game/") or level_path.endswith("/"):
        return skill_error("Invalid level_path", "level_path must be a /Game/... asset path")
    if template_path and not template_path.startswith(("/Game/", "/Engine/Maps/Templates/")):
        return skill_error("Invalid template_path", "template_path must be a /Game/... level or an engine template")

    import unreal  # noqa: PLC0415

    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        return skill_error("Level already exists", f"An asset already exists at '{level_path}'")
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    created = subsystem is not None and (
        subsystem.new_level_from_template(level_path, template_path) if template_path else subsystem.new_level(level_path)
    )
    if not created:
        return skill_error("Failed to create level", f"LevelEditorSubsystem rejected '{level_path}'")
    if not unreal.EditorLevelLibrary.save_current_level():
        return skill_error("Failed to save level", f"Could not save '{level_path}'")
    if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
        return skill_error("Level verification failed", f"Saved level '{level_path}' is not in the asset registry")

    return skill_success(
        f"Created level '{level_path}'",
        level_path=level_path,
        prompt="Use unreal_actors__spawn_actor to populate the new level.",
    )


def main(**kwargs) -> dict:
    return create_level(**kwargs)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
