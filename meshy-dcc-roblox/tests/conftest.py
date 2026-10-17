import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Core writes logs, job databases and skill folders under the home directory."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home
