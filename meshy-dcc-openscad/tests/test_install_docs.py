from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_guide_documents_the_supported_matrix() -> None:
    guide = (ROOT / "install.md").read_text(encoding="utf-8")

    from meshy_dcc_openscad.compat import supported_range_labels

    for label in supported_range_labels():
        assert "`%s`" % label in guide


def test_install_guide_names_the_verbs_the_catalog_runs() -> None:
    guide = (ROOT / "install.md").read_text(encoding="utf-8")

    assert "install-project <project> --openscad <exe>" in guide
    assert "serve --project <project>" in guide
    assert "openscad_host_version_unlisted" in guide
