from pathlib import Path

import meshy_dcc_material_maker
from meshy_dcc_material_maker.server import MaterialMakerMcpServer


def test_server_is_standalone_and_bundles_typed_skill(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHY_DCC_DISABLE_DEFAULT_SKILL_PATHS", "1")
    server = MaterialMakerMcpServer(port=0, registry_dir=str(tmp_path / "registry"))
    assert server._options.instance_type == "standalone"
    skill_file = (
        Path(meshy_dcc_material_maker.__file__).parent
        / "skills"
        / "material-maker-materials"
        / "SKILL.md"
    )
    assert skill_file.is_file()
