from pathlib import Path

from meshy_dcc_godot import __version__

ROOT = Path(__file__).parents[1]


def test_version_metadata_is_synchronized():
    assert f'version = "{__version__}"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_addon_and_roguelike_templates_are_packaged():
    addon = ROOT / "src" / "meshy_dcc_godot" / "godot_addon" / "addons" / "meshy_dcc_godot"
    assert (addon / "plugin.cfg").is_file()
    assert (addon / "plugin.gd").is_file()
    assert (addon / "commands.gd").is_file()
    assert (addon / "templates" / "roguelike" / "game.gd").is_file()
    assert (addon / "templates" / "roguelike" / "ci_smoke.gd").is_file()
    assert (
        ROOT / "src" / "meshy_dcc_godot" / "schemas" / "playtest_actions_manifest_v1.schema.json"
    ).is_file()


def test_godot_export_skill_ships_cross_platform_packaging_guidance():
    skill = ROOT / "src" / "meshy_dcc_godot" / "skills" / "godot-export"
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    guide_path = skill / "references" / "platform-packaging.md"

    assert "references/platform-packaging.md" in skill_text
    assert guide_path.is_file()

    guide = guide_path.read_text(encoding="utf-8")
    for platform in ("Windows", "macOS", "Linux", "Web", "Android"):
        assert f"## {platform}" in guide
    assert "C:/Windows/Fonts" in guide
    assert "bundled font" in guide.lower()
    assert "CJK" in guide
    assert "exported artifact" in guide


def test_install_sop_is_public_and_canonical_console_is_packaged():
    guide = (ROOT / "install.md").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for verb in ("install", "status", "verify", "uninstall", "upgrade"):
        assert f"meshy-dcc-godot {verb}" in guide
    for platform in ("Windows", "macOS", "Linux"):
        assert platform in guide
    assert 'meshy-dcc-godot = "meshy_dcc_godot.cli:main"' in project
    assert 'meshy-dcc-godot-install = "meshy_dcc_godot.install:main"' in project
