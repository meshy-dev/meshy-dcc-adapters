"""prepare_official_mcp keeps the user's INI bytes and never leaves a half-configured project."""

from __future__ import annotations

import json

import pytest
from test_official_mcp import _load_prepare_module


@pytest.fixture
def setup_project(tmp_path, monkeypatch):
    prepare = _load_prepare_module()
    engine = tmp_path / "Engine"
    plugins = engine / "Plugins"
    project = tmp_path / "Project" / "Example.uproject"
    project.parent.mkdir()
    project.write_bytes(b'\xef\xbb\xbf{\r\n "FileVersion": 3, "Description": "Keep me", "Plugins": []\r\n}\r\n')
    config = project.parent / "Config" / "DefaultEditorPerProjectUserSettings.ini"
    monkeypatch.setattr(
        prepare, "_process_arguments", lambda: [str(engine / "Binaries" / "UnrealEditor"), str(project)]
    )
    for relative in prepare._PLUGIN_RELATIVE_PATHS.values():
        path = plugins / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"FileVersion": 3}', encoding="utf-8")
    return prepare, project, config


def _assert_no_writes(prepare, monkeypatch):
    def unexpected_write(*args):
        pytest.fail("A preflight failure must not write")

    monkeypatch.setattr(prepare, "_atomic_write_bytes", unexpected_write)


def test_first_run_enables_plugins_and_writes_settings_then_repeats_without_writing(setup_project, monkeypatch):
    prepare, project, config = setup_project

    result = prepare.prepare_official_mcp()

    assert result["success"] is True
    assert result["context"]["changed_plugins"] == ["ModelContextProtocol", "EditorToolset"]
    assert result["context"]["config_changed"] is True
    assert result["context"]["configuration_verified"] is True
    assert json.loads(project.read_bytes())["Description"] == "Keep me"
    assert b"ServerPortNumber=8000" in config.read_bytes()

    before = project.read_bytes(), config.read_bytes()
    _assert_no_writes(prepare, monkeypatch)
    repeated = prepare.prepare_official_mcp()
    assert repeated["success"] is True
    assert repeated["context"]["changed_plugins"] == []
    assert repeated["context"]["config_changed"] is False
    assert (project.read_bytes(), config.read_bytes()) == before


def test_unrelated_ini_bytes_comments_duplicates_and_arrays_are_preserved(setup_project):
    prepare, project, config = setup_project
    config.parent.mkdir()
    original = (
        b"\xef\xbb\xbf; Keep this comment and CRLF\r\n[Other]\r\n"
        b"Repeated=one\r\nRepeated=two\r\n+Array=one\r\n+Array=two\r\n"
        b"-Array=gone\r\n!Array=ClearArray\r\n.Array=duplicate\r\n"
        b"[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]\r\n"
        b"; Keep MCP comment\r\nServerPortNumber=42\r\nUnrelated=keep\r\n"
        b"[Other]\r\nPreserveNoFinalNewline=yes"
    )
    config.write_bytes(original)

    assert prepare.prepare_official_mcp()["success"] is True

    updated = config.read_bytes()
    assert updated.startswith(original)
    suffix = updated[len(original) :]
    assert b"ServerPortNumber=8000\r\n" in suffix
    assert suffix.count(b"\n") == suffix.count(b"\r\n")
    assert prepare._configure_autostart(config) is False
    assert config.read_bytes() == updated


def test_ini_section_case_and_default_section_follow_unreal_semantics(setup_project):
    prepare, _project, _config = setup_project
    desired = "\n".join(f"{key}={value}" for key, value in prepare._AUTOSTART_SETTINGS.items())
    inherited = f"[DEFAULT]\n{desired}\n[{prepare._MCP_SECTION}]\n".encode()
    assert prepare._render_autostart(inherited) != inherited
    overrides = f"[{prepare._MCP_SECTION}]\n{desired}\n[{prepare._MCP_SECTION.lower()}]\nServerPortNumber=42\n".encode()
    corrected = prepare._render_autostart(overrides)
    assert corrected != overrides
    assert prepare._render_autostart(corrected) == corrected


@pytest.mark.parametrize("command", ["+", "-", ".", "!"])
def test_a_later_ini_command_on_a_setting_is_not_reported_as_ready(setup_project, command):
    prepare, _project, _config = setup_project
    original = prepare._render_autostart(None) + f"{command}ServerPortNumber=8000\n".encode()

    corrected = prepare._render_autostart(original)

    assert corrected.startswith(original)
    assert corrected != original
    assert prepare._render_autostart(corrected) == corrected


@pytest.mark.parametrize("config_contents", [b"key=value\n", b"[Unclosed\n", b"[Valid]\nbroken\n", b"\xff"])
def test_malformed_ini_blocks_before_the_project_is_written(setup_project, config_contents, monkeypatch):
    prepare, project, config = setup_project
    config.parent.mkdir()
    config.write_bytes(config_contents)
    project_original = project.read_bytes()
    _assert_no_writes(prepare, monkeypatch)

    result = prepare.prepare_official_mcp()

    assert result["success"] is False
    assert project.read_bytes() == project_original
    assert config.read_bytes() == config_contents


def test_ini_diagnostic_leaves_out_the_configuration_text(setup_project):
    prepare, _project, config = setup_project
    config.parent.mkdir()
    config.write_bytes(b"[Valid]\nsecret-token-value\n")

    result = prepare.prepare_official_mcp()

    assert result["error"] == "invalid_editor_ini"
    assert result["context"]["line_numbers"] == [2]
    assert "secret-token-value" not in json.dumps(result)


@pytest.mark.parametrize("project_contents", [b"{ broken", b"[]", b'{"Plugins": {}}', b"\xff"])
def test_invalid_project_blocks_without_writes(setup_project, project_contents, monkeypatch):
    prepare, project, config = setup_project
    project.write_bytes(project_contents)
    _assert_no_writes(prepare, monkeypatch)

    assert prepare.prepare_official_mcp()["success"] is False
    assert project.read_bytes() == project_contents
    assert not config.parent.exists()


@pytest.mark.parametrize("existing_config", [False, True])
@pytest.mark.parametrize("fail_after_replace", [False, True])
def test_a_failed_second_write_restores_both_files_exactly(
    setup_project, monkeypatch, existing_config, fail_after_replace
):
    prepare, project, config = setup_project
    config_original = b"\xef\xbb\xbf; unchanged\r\n[Other]\r\nRepeated=1\r\nRepeated=2\r\n"
    if existing_config:
        config.parent.mkdir()
        config.write_bytes(config_original)
    project_original = project.read_bytes()
    actual_write = prepare._atomic_write_bytes
    attempts = []

    def fail_second_write(path, contents):
        attempts.append(path)
        if len(attempts) == 2:
            if fail_after_replace:
                actual_write(path, contents)
            raise OSError("Injected second-write failure")
        actual_write(path, contents)

    monkeypatch.setattr(prepare, "_atomic_write_bytes", fail_second_write)

    result = prepare.prepare_official_mcp()

    assert result["success"] is False
    assert result["error"] == "configuration_write_failed"
    assert result["context"]["rollback_complete"] is True
    assert project.read_bytes() == project_original
    assert config.read_bytes() == config_original if existing_config else not config.exists()


def test_an_incomplete_rollback_names_the_file_it_could_not_restore(setup_project, monkeypatch):
    prepare, project, config = setup_project
    config.parent.mkdir()
    config.write_bytes(b"; existing\n")  # restoring it takes a write, not just an unlink
    actual_write = prepare._atomic_write_bytes
    attempts = []

    def fail_every_write_after_the_first(path, contents):
        attempts.append(path)
        if len(attempts) > 1:
            raise OSError("Injected write failure")
        actual_write(path, contents)

    monkeypatch.setattr(prepare, "_atomic_write_bytes", fail_every_write_after_the_first)

    result = prepare.prepare_official_mcp()

    assert result["error"] == "configuration_rollback_failed"
    assert result["context"]["rollback_complete"] is False
    assert result["context"]["rollback_errors"] == [{"path": str(config), "error": "Injected write failure"}]


def test_a_readback_mismatch_fails_and_leaves_the_unexpected_bytes_alone(setup_project, monkeypatch):
    prepare, project, config = setup_project
    actual_write = prepare._atomic_write_bytes

    def write_then_lose_the_bytes(path, contents):
        actual_write(path, contents + b" " if path == project else contents)

    monkeypatch.setattr(prepare, "_atomic_write_bytes", write_then_lose_the_bytes)

    result = prepare.prepare_official_mcp()

    assert result["success"] is False
    assert "readback mismatch" in result["context"]["details"]
    # The INI was written as intended, so it is restored; the project holds bytes
    # we did not write, so rollback does not overwrite them and says so.
    assert not config.exists()
    assert result["error"] == "configuration_rollback_failed"
    assert result["context"]["rollback_errors"] == [
        {"path": str(project), "error": "Configuration changed externally; left untouched"}
    ]


@pytest.mark.parametrize("timing", ["before", "during"])
def test_a_file_changed_by_someone_else_is_not_overwritten(setup_project, monkeypatch, timing):
    prepare, project, config = setup_project
    config.parent.mkdir()
    config.write_bytes(b"; mine\n")
    external = b"; changed while we worked\n"
    actual_write = prepare._atomic_write_bytes

    def write(path, contents):
        if timing == "during" and path == project:
            config.write_bytes(external)
        actual_write(path, contents)

    if timing == "before":
        actual_read = prepare._read_optional_bytes
        reads = []

        def read(path):
            value = actual_read(path)
            if path == config:
                reads.append(path)
                if len(reads) == 1:
                    config.write_bytes(external)
            return value

        monkeypatch.setattr(prepare, "_read_optional_bytes", read)
    monkeypatch.setattr(prepare, "_atomic_write_bytes", write)

    result = prepare.prepare_official_mcp()

    assert result["success"] is False
    assert config.read_bytes() == external


def test_atomic_replace_failure_keeps_the_original_and_removes_the_temporary_file(tmp_path, monkeypatch):
    prepare = _load_prepare_module()
    target = tmp_path / "test.ini"
    target.write_bytes(b"exact original")

    def fail_replace(source, destination):
        raise OSError("Injected atomic replace failure")

    monkeypatch.setattr(prepare.os, "replace", fail_replace)
    with pytest.raises(OSError, match="atomic replace"):
        prepare._atomic_write_bytes(target, b"replacement")
    assert target.read_bytes() == b"exact original"
    assert list(tmp_path.iterdir()) == [target]
