from __future__ import annotations

import re
from pathlib import Path

import meshy_dcc_substance3d_painter as adapter

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_synchronized():
    version = re.search(r'(?m)^version = "([^"]+)"$', ROOT.joinpath("pyproject.toml").read_text(encoding="utf-8"))
    assert version is not None
    assert version.group(1) == adapter.__version__


def test_plugin_and_skill_contract_files_exist():
    package = ROOT / "src" / "meshy_dcc_substance3d_painter"
    for required_directory in ("plugins", "startup", "modules"):
        assert package.joinpath("painter", required_directory).is_dir()
    startup_entry = package.joinpath("painter", "startup", f"{adapter.STARTUP_PLUGIN_MODULE}.py")
    assert startup_entry.exists()
    assert adapter.STARTUP_PLUGIN_MODULE != adapter.__name__
    assert not package.joinpath("painter", "plugins", f"{adapter.STARTUP_PLUGIN_MODULE}.py").exists()
    assert package.joinpath("skills", "painter-project", "SKILL.md").exists()
    assert package.joinpath("skills", "painter-project", "tools.yaml").exists()
    assert package.joinpath("materialized_script_executor.py").exists()
    assert package.joinpath("skills", "painter-project", "scripts", "execute_materialized_script.py").exists()
