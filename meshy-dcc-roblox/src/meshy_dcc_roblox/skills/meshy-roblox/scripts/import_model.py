from pathlib import Path

from meshy_dcc_core.skill import skill_entry, skill_success

from meshy_dcc_roblox.bridge import call_host
from meshy_dcc_roblox.meshy_import import MAX_TEXTURE, STUDS_PER_METER, prepare, send


@skill_entry
def main(
    path: str,
    name: str = "",
    parent: str = "Workspace",
    position: list = None,
    scale: float = STUDS_PER_METER,
    flip_v: bool = False,
    max_texture_size: int = MAX_TEXTURE,
    publish: bool = False,
    **_kwargs,
):
    source = Path(path)
    payload = prepare(source, scale=scale, flip_v=flip_v, max_texture=max_texture_size)
    options = {"name": name or source.stem, "parent": parent, "publish": publish}
    if position:
        options["position"] = position
    result = send(call_host, payload, options)
    note = (
        "Model built from uploaded assets; it persists with the place."
        if publish
        else "Model built in this Studio session only; Roblox does not save editable meshes "
        "with the place. Publish (with the user's consent) to keep it."
    )
    return skill_success(note, **result)


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
