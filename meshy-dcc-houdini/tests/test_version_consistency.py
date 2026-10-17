"""Keep the meshy-dcc-core range and the adapter version in step everywhere they are declared."""

from __future__ import annotations

import re
from pathlib import Path

from meshy_dcc_houdini import __version__, _installer

ROOT = Path(__file__).resolve().parents[1]
CORE_RANGE = "meshy-dcc-core>=0.2.0,<0.3.0"


def test_core_range_is_declared_once_everywhere() -> None:
    assert CORE_RANGE in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert _installer.MIN_CORE_VERSION == "0.2.0"
    packaging = (ROOT / "packaging" / "build_package.py").read_text(encoding="utf-8")
    assert 'MIN_CORE_VERSION = "0.2.0"' in packaging
    assert 'MAX_CORE_VERSION_EXCLUSIVE = "0.3.0"' in packaging
    assert CORE_RANGE in (ROOT / "README.md").read_text(encoding="utf-8").replace(" ", "")


def test_adapter_version_matches_pyproject() -> None:
    match = re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None and match.group(1) == __version__


def test_skill_compatibility_names_this_core_line() -> None:
    for skill_md in sorted((ROOT / "src" / "meshy_dcc_houdini" / "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        declared = re.search(r"meshy-dcc-core\s+([0-9]+\.[0-9]+\.[0-9]+)", text)
        assert declared and declared.group(1) == "0.2.0", skill_md.parent.name
