"""The installer writes, reports and removes only its own startup loader."""

from __future__ import annotations

import json
import subprocess
import sys

from meshy_dcc_substance3d_painter import install_cli


def _run(tmp_path, monkeypatch, capsys, *argv):
    """Run the CLI against a profile and an extracted-package payload under ``tmp_path``."""
    payload = tmp_path / "package" / "plugin" / "python"
    for package in ("meshy_dcc_core", "meshy_dcc_substance3d_painter"):
        (payload / package).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(install_cli, "payload_dir", lambda: payload)
    monkeypatch.setenv(install_cli.PROFILE_ENV, str(tmp_path / "profile"))
    code = install_cli.main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_install_plans_then_writes_then_is_current(tmp_path, monkeypatch, capsys):
    loader = tmp_path / "profile" / "python" / "startup" / install_cli.LOADER_NAME
    code, plan = _run(tmp_path, monkeypatch, capsys, "install")
    assert (code, plan["status"], plan["applied"]) == (0, "planned", False)
    assert not loader.exists()

    code, done = _run(tmp_path, monkeypatch, capsys, "install", "--yes")
    assert (code, done["status"], done["applied"]) == (0, "installed", True)
    assert done["loader_path"] == str(loader)
    assert loader.read_text(encoding="utf-8").startswith(install_cli.MARKER)

    code, again = _run(tmp_path, monkeypatch, capsys, "install", "--yes")
    assert (code, again["status"]) == (0, "current")

    code, status = _run(tmp_path, monkeypatch, capsys, "status")
    assert (status["status"], status["installed_payload"]) == (
        "installed",
        str(tmp_path / "package" / "plugin" / "python"),
    )


def test_uninstall_removes_only_the_loader(tmp_path, monkeypatch, capsys):
    _run(tmp_path, monkeypatch, capsys, "install", "--yes")
    startup = tmp_path / "profile" / "python" / "startup"
    (startup / "someone_elses_plugin.py").write_text("x = 1\n", encoding="utf-8")
    (startup / "__pycache__").mkdir()
    (startup / "__pycache__" / "meshy_dcc_substance3d_painter_plugin.cpython-311.pyc").write_bytes(b"")

    code, plan = _run(tmp_path, monkeypatch, capsys, "uninstall")
    assert (code, plan["status"]) == (0, "planned")
    assert (startup / install_cli.LOADER_NAME).exists()

    code, done = _run(tmp_path, monkeypatch, capsys, "uninstall", "--yes")
    assert (code, done["status"]) == (0, "uninstalled")
    assert sorted(p.name for p in startup.iterdir()) == ["someone_elses_plugin.py"]

    code, again = _run(tmp_path, monkeypatch, capsys, "uninstall", "--yes")
    assert (code, again["status"]) == (0, "not_installed")


def test_an_incomplete_payload_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(install_cli.PROFILE_ENV, str(tmp_path / "profile"))
    monkeypatch.setattr(install_cli, "payload_dir", lambda: tmp_path / "empty")
    assert install_cli.main(["install", "--yes", "--json"]) == install_cli.EXIT_REFUSED
    assert not (tmp_path / "profile").exists()


def test_a_foreign_file_of_the_same_name_is_never_touched(tmp_path, monkeypatch, capsys):
    loader = tmp_path / "profile" / "python" / "startup" / install_cli.LOADER_NAME
    loader.parent.mkdir(parents=True)
    loader.write_text("print('mine')\n", encoding="utf-8")
    for verb in ("install", "uninstall"):
        code, result = _run(tmp_path, monkeypatch, capsys, verb, "--yes")
        assert (code, result["status"]) == (install_cli.EXIT_REFUSED, "refused")
    assert loader.read_text(encoding="utf-8") == "print('mine')\n"
    assert _run(tmp_path, monkeypatch, capsys, "status")[1]["status"] == "foreign"


def test_the_written_loader_starts_the_adapter_from_its_payload(tmp_path):
    """Painter imports the loader by file; it must expose start/close from the recorded payload only."""
    payload = install_cli.payload_dir()
    loader = tmp_path / install_cli.LOADER_NAME
    loader.write_text(install_cli.loader_source(payload), encoding="utf-8")
    probe = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('meshy_dcc_substance3d_painter_plugin', {str(loader)!r})\n"
        "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n"
        "assert callable(module.start_plugin) and callable(module.close_plugin)\n"
        "print(sys.path[0])\n"
    )
    out = subprocess.run([sys.executable, "-I", "-c", probe], capture_output=True, text=True, check=True).stdout
    assert out.strip() == str(payload)


def test_a_loader_whose_payload_is_gone_fails_with_a_clear_message(tmp_path):
    loader = tmp_path / install_cli.LOADER_NAME
    loader.write_text(install_cli.loader_source(tmp_path / "removed"), encoding="utf-8")
    run = subprocess.run([sys.executable, "-I", str(loader)], capture_output=True, text=True)
    assert run.returncode != 0
    assert "no longer installed" in run.stderr
