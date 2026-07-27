from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import drydock_codex
import scaffold_bundle


def _runtime_revision() -> str:
    manifest = json.loads(
        (
            drydock_codex.PLUGIN_ROOT / "hooks" / "runtime.manifest.json"
        ).read_text(encoding="utf-8")
    )
    return manifest["files"][0]["sha256"]


def _write_liveness(
    plugin_data: Path,
    session_id: str,
    repository: Path,
    *,
    project_root: Path | None = None,
) -> None:
    path = plugin_data / "liveness" / f"{session_id}.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session_id": session_id,
                "runtime_sha256": _runtime_revision(),
                "project_root": str((project_root or repository).resolve()),
                "model": "gpt-test",
                "permission_mode": "default",
            }
        ),
        encoding="utf-8",
    )


def test_init_preview_does_not_write(tmp_path: Path) -> None:
    repository = tmp_path / "new-repository"
    report = drydock_codex.initialize(repository, apply=False)
    assert report["mode"] == "preview"
    assert report["applied"] is False
    assert len(report["planned"]["create"]) == 40
    assert report["created"] == []
    assert not repository.exists()


def test_init_apply_creates_scaffold_and_is_idempotent(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    first = drydock_codex.initialize(repository, apply=True)
    assert first["applied"] is True
    assert len(first["created"]) == 40
    assert not (repository / "CLAUDE.md").exists()
    assert not (repository / ".codex" / "hooks.json").exists()
    assert not (repository / ".git" / "hooks" / "pre-commit").exists()

    second = drydock_codex.initialize(repository, apply=True)
    assert second["applied"] is True
    assert second["created"] == []
    assert second["conflicts"] == []
    assert len(second["unchanged"]) == 40


def test_init_preserves_existing_file_and_reports_conflict(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    existing = repository / "AGENTS.md"
    existing.write_text("owner content\n", encoding="utf-8")

    report = drydock_codex.initialize(repository, apply=True)
    assert report["applied"] is True
    assert "AGENTS.md" in report["conflicts"]
    assert existing.read_text(encoding="utf-8") == "owner content\n"


def test_init_merges_only_missing_gitignore_lines(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    gitignore = repository / ".gitignore"
    gitignore.write_text("# owner\n.env\n", encoding="utf-8")

    report = drydock_codex.initialize(repository, apply=True)
    assert report["applied"] is True
    assert report["gitignore_added"]
    final = gitignore.read_text(encoding="utf-8")
    assert final.startswith("# owner\n.env\n")
    for line in report["gitignore_added"]:
        assert final.splitlines().count(line) == 1


def test_init_refuses_symlinked_parent(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    outside = tmp_path / "outside"
    repository.mkdir()
    outside.mkdir()
    link = repository / "scripts"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not permitted on this Windows installation")

    with pytest.raises(scaffold_bundle.BundleError, match="symlink"):
        drydock_codex.initialize(repository, apply=True)
    assert list(outside.iterdir()) == []


def test_init_lock_failure_does_not_report_planned_files_as_created(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / drydock_codex.LOCK_NAME).write_text("active\n", encoding="utf-8")

    report = drydock_codex.initialize(repository, apply=True)
    assert report["applied"] is False
    assert report["created"] == []
    assert report["errors"]
    assert report["planned"]["create"]


def test_readiness_reports_positive_evidence_and_unknowns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    repository = tmp_path / "repository"
    drydock_codex.initialize(repository, apply=True)
    (repository / "PROJECT_CONTEXT.md").write_text(
        "# Product\n\nA confirmed, project-specific outcome for real users.\n",
        encoding="utf-8",
    )

    report = drydock_codex.readiness(repository)
    assert report["plugin"]["status"] == "valid"
    assert report["bundle"]["status"] == "valid"
    assert report["repository"]["initialized"] is True
    assert report["repository"]["project_context"] == "real"
    assert report["ready_for_lifecycle"] is True
    assert report["ready_for_enforcement"] is False
    assert report["enforcement"]["active"] is False
    assert report["enforcement"]["trusted"] == "unknown"
    assert report["enforcement"]["active_task_liveness"] == "unavailable"
    assert report["enforcement"]["definition"] == "valid"
    assert report["enforcement"]["handler_revision"]
    assert report["enforcement"]["defined_tool_contracts"] == [
        "Bash",
        "apply_patch",
    ]
    assert report["peer"]["status"] == "not_checked"


def test_readiness_discovers_current_desktop_liveness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    drydock_codex.initialize(repository, apply=True)
    session_id = "desktop-task-123"
    codex_home = tmp_path / "codex-home"
    plugin_data = codex_home / "plugins" / "data" / "drydock-drydock"
    _write_liveness(plugin_data, session_id, repository)
    monkeypatch.setenv("CODEX_THREAD_ID", session_id)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)

    report = drydock_codex.readiness(repository)

    enforcement = report["enforcement"]
    assert enforcement["active_task_liveness"] == "current_revision_observed"
    assert enforcement["liveness_evidence"]["session_id"] == session_id
    assert enforcement["liveness_evidence"]["project_root"] == str(
        repository.resolve()
    )
    assert enforcement["liveness_resolution"] == {
        "session_id_source": "CODEX_THREAD_ID",
        "plugin_data_source": "codex_home_plugin_data",
        "session_error": None,
        "plugin_data_error": None,
    }
    assert enforcement["active"] is False
    assert report["ready_for_enforcement"] is False


def test_readiness_rejects_repository_mismatched_liveness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    other_repository = tmp_path / "other"
    drydock_codex.initialize(repository, apply=True)
    other_repository.mkdir()
    session_id = "desktop-task-456"
    codex_home = tmp_path / "codex-home"
    plugin_data = codex_home / "plugins" / "data" / "drydock-drydock"
    _write_liveness(
        plugin_data,
        session_id,
        repository,
        project_root=other_repository,
    )
    monkeypatch.setenv("CODEX_THREAD_ID", session_id)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)

    report = drydock_codex.readiness(repository)

    assert (
        report["enforcement"]["active_task_liveness"]
        == "stale_or_mismatched"
    )
    assert report["enforcement"]["liveness_evidence"] is None


def test_readiness_refuses_ambiguous_plugin_data_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    drydock_codex.initialize(repository, apply=True)
    session_id = "desktop-task-789"
    codex_home = tmp_path / "codex-home"
    for name in ("drydock-one", "drydock-two"):
        _write_liveness(
            codex_home / "plugins" / "data" / name,
            session_id,
            repository,
        )
    monkeypatch.setenv("CODEX_THREAD_ID", session_id)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)

    report = drydock_codex.readiness(repository)

    enforcement = report["enforcement"]
    assert enforcement["active_task_liveness"] == "unavailable"
    assert enforcement["liveness_evidence"] is None
    assert enforcement["liveness_resolution"]["plugin_data_source"] == "ambiguous"
    assert (
        enforcement["liveness_resolution"]["plugin_data_error"]
        == "current task liveness record exists in multiple plugin-data roots"
    )


def test_explicit_liveness_arguments_override_environment_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    drydock_codex.initialize(repository, apply=True)
    explicit_session = "explicit-task"
    explicit_data = tmp_path / "explicit-plugin-data"
    _write_liveness(explicit_data, explicit_session, repository)
    monkeypatch.setenv("CODEX_THREAD_ID", "ambient-task")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "empty-codex-home"))
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)

    report = drydock_codex.readiness(
        repository,
        session_id=explicit_session,
        plugin_data=explicit_data,
    )

    enforcement = report["enforcement"]
    assert enforcement["active_task_liveness"] == "current_revision_observed"
    assert enforcement["liveness_resolution"]["session_id_source"] == "argument"
    assert enforcement["liveness_resolution"]["plugin_data_source"] == "argument"


def test_readiness_does_not_treat_template_context_as_ready(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    drydock_codex.initialize(repository, apply=True)
    template = repository / "PROJECT_CONTEXT.template.md"
    (repository / "PROJECT_CONTEXT.md").write_bytes(template.read_bytes())

    report = drydock_codex.readiness(repository)
    assert report["repository"]["project_context"] == "template"
    assert report["ready_for_lifecycle"] is False
    assert "PROJECT_CONTEXT.md does not contain confirmed project context" in report[
        "blockers"
    ]


def test_init_output_digest_matches_verified_bundle(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    report = drydock_codex.initialize(repository, apply=True)
    entries = scaffold_bundle.load_bundle(drydock_codex.BUNDLE_PATH)
    agents = next(entry for entry in entries if entry.path == "AGENTS.md")
    assert hashlib.sha256((repository / "AGENTS.md").read_bytes()).hexdigest() == (
        agents.sha256
    )
    assert report["bundle_sha256"] == hashlib.sha256(
        drydock_codex.BUNDLE_PATH.read_bytes()
    ).hexdigest()
