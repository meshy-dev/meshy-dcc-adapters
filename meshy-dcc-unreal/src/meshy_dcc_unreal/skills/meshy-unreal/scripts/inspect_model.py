"""Read back a Meshy model: a level actor by label, or a static mesh asset."""

from __future__ import annotations

from _meshy import actor_info, find_actor, mesh_info
from meshy_dcc_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def inspect_model(actor: str = "", asset: str = "", **kwargs) -> dict:
    import unreal  # noqa: PLC0415

    if bool(actor) == bool(asset):
        return skill_error("Pass exactly one of actor or asset", "actor is a level actor label; asset an object path")
    if actor:
        found = find_actor(unreal, actor)
        if found is None:
            return skill_error(f"No actor labelled {actor!r} in the open level", "List actors with unreal-actors")
        return skill_success(f"Read back actor {actor}", model=actor_info(unreal, found))
    loaded = unreal.EditorAssetLibrary.load_asset(asset)
    if loaded is None:
        return skill_error(f"No asset at {asset}", "Pass an object path such as /Game/Meshy/Name/Name")
    return skill_success(f"Read back asset {asset}", model=mesh_info(unreal, loaded))
