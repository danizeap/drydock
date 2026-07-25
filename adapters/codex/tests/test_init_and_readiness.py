from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import drydock_codex
import scaffold_bundle


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


def test_readiness_reports_positive_evidence_and_unknowns(tmp_path: Path) -> None:
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
