import json
from pathlib import Path

from meshy_dcc_unreal.__version__ import __version__

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DESCRIPTOR = ROOT / "unreal" / "plugin" / "MeshyDccUnreal.uplugin"


def test_plugin_is_python_only_and_meshy_branded() -> None:
    descriptor = json.loads(PLUGIN_DESCRIPTOR.read_text(encoding="utf-8"))

    # No C++ module: the editor loads the plugin without compiling anything.
    assert "Modules" not in descriptor
    assert descriptor["VersionName"] == __version__
    assert descriptor["CreatedBy"] == "Meshy"
    assert descriptor["CreatedByURL"] == "https://www.meshy.ai"
    required = {entry["Name"] for entry in descriptor["Plugins"] if not entry.get("Optional")}
    assert required == {"PythonScriptPlugin", "EditorScriptingUtilities"}
