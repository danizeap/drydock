from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import process_runner


FAKE_CODEX = Path(__file__).with_name("fake_codex.py")


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "owner"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "drydock-test@example.invalid")
    _git(repo, "config", "user.name", "Drydock Test")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    (repo / ".gitignore").write_text(".drydock-worktrees/\n", encoding="utf-8")
    _git(repo, "add", "README.md", ".gitignore")
    _git(repo, "commit", "-m", "initial")
    return repo


def _prefix() -> list[str]:
    return [sys.executable, str(FAKE_CODEX)]


def test_process_identity_is_exact_for_current_process() -> None:
    state, identity = process_runner.process_identity_state(os.getpid())
    assert state == "alive"
    assert identity is not None
    assert process_runner.exact_process_liveness(identity.as_dict()) == "alive"


def test_mutation_container_is_repo_local_and_must_be_ignored(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    container = process_runner._worktree_root(repo)
    assert container.parent == repo.resolve()

    (repo / ".gitignore").write_text("", encoding="utf-8")
    with pytest.raises(process_runner.RunnerError, match="must be ignored"):
        process_runner._worktree_root(repo)


def test_runner_git_uses_a_pinned_absolute_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    observed: list[list[str]] = []
    original = process_runner.subprocess.run

    def capture(
        arguments: list[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        observed.append(list(arguments))
        return original(arguments, *args, **kwargs)

    monkeypatch.setattr(process_runner.subprocess, "run", capture)
    process_runner._run_git(repo, ["rev-parse", "HEAD"])
    process_runner._worktree_root(repo)
    assert len(observed) == 2
    for arguments in observed:
        executable = Path(arguments[0])
        assert executable.is_absolute()
        assert executable.name.casefold() in {"git", "git.exe"}
        assert arguments[0] != "git"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("filter.hostile.clean", "hostile-filter-command"),
        ("include.path", "../unfingerprinted-config"),
    ],
)
def test_mutation_refuses_executable_or_included_local_git_config_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: str,
) -> None:
    repo = _repository(tmp_path)
    log = tmp_path / "fake-log.json"
    _git(repo, "config", key, value)
    monkeypatch.setenv("DRYDOCK_FAKE_LOG", str(log))
    with pytest.raises(
        process_runner.RunnerError,
        match="local Git config includes or external filter",
    ):
        process_runner.mutate(
            repo,
            "must refuse before delegated execution",
            "gpt-test",
            timeout=30,
            codex_prefix=_prefix(),
        )
    assert not log.exists()
    assert _git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_lease_is_exclusive_and_releases_exact_record(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    path = tmp_path / "leases" / "lease.json"
    lease = process_runner.Lease.acquire(
        path,
        worktree,
        "codex/drydock/test",
        worker_timeout=30,
        cleanup_grace=10,
    )
    with pytest.raises(process_runner.RunnerError, match="active lease"):
        process_runner.Lease.acquire(
            path,
            worktree,
            "codex/drydock/test",
            worker_timeout=30,
            cleanup_grace=10,
        )
    lease.release()
    assert not path.exists()


def test_stale_lease_reclaims_only_after_dead_process_proof(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    path = tmp_path / "leases" / "lease.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "worktree": str(worktree.resolve()),
                "branch": "codex/drydock/test",
                "phase": "running",
                "process": {"pid": 99999999, "started": "gone"},
                "started_epoch": 0,
                "deadline_epoch": 0,
                "cleanup_grace_seconds": 1,
            }
        ),
        encoding="utf-8",
    )
    lease = process_runner.Lease.acquire(
        path,
        worktree,
        "codex/drydock/test",
        worker_timeout=30,
        cleanup_grace=10,
    )
    assert lease.record["phase"] == "launching"
    lease.release()


def test_stale_lease_refuses_uncertain_liveness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    path = tmp_path / "lease.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "worktree": str(worktree.resolve()),
                "branch": "codex/drydock/test",
                "phase": "running",
                "process": {"pid": 123, "started": "unknown"},
                "started_epoch": 0,
                "deadline_epoch": 0,
                "cleanup_grace_seconds": 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(process_runner, "exact_process_liveness", lambda _record: "uncertain")
    with pytest.raises(process_runner.RunnerError, match="uncertain"):
        process_runner.Lease.acquire(
            path,
            worktree,
            "codex/drydock/test",
            worker_timeout=30,
            cleanup_grace=10,
        )
    assert path.exists()


def test_mutation_uses_fixed_worktree_process_and_never_merges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    log = tmp_path / "fake-log.json"
    monkeypatch.setenv("DRYDOCK_FAKE_LOG", str(log))
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")

    result = process_runner.mutate(
        repo,
        "add a bounded worker file",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )

    assert result["ok"] is False
    assert result["stage"] == "awaiting_verification"
    assert result["merged"] is False
    assert result["owner_unchanged"] is True
    assert result["git_control_unchanged"] is True
    assert result["lease_released"] is True
    assert result["branch"].startswith(process_runner.BRANCH_PREFIX)
    assert result["changed_files"] == ["worker.py"]
    assert result["ignored_files"] == []
    assert result["test_evidence"]["verdict"] == "blocked"
    assert not (repo / "worker.py").exists()

    call = json.loads(log.read_text(encoding="utf-8"))
    argv = call["argv"]
    assert argv[argv.index("-s") + 1] == "workspace-write"
    assert argv[argv.index("-C") + 1] == result["worktree"]
    assert "--ephemeral" in argv
    assert "--ignore-user-config" not in argv
    assert "--ignore-rules" in argv
    overrides = [
        argv[index + 1] for index, value in enumerate(argv) if value == "-c"
    ]
    assert overrides == list(process_runner.FIXED_CONFIG_OVERRIDES)
    disabled = [
        argv[index + 1] for index, value in enumerate(argv) if value == "--disable"
    ]
    assert disabled == list(process_runner.FIXED_DISABLED_FEATURES)
    assert "danger-full-access" not in argv
    assert "Do not stage, commit, branch, merge, push" in call["prompt"]
    assert (
        result["worker"]["argv_contract"][
            "windows_job_descendant_lifetime_contained"
        ]
        is (os.name == "nt")
    )


@pytest.mark.parametrize("poison", ["owner", "delete"])
def test_worker_git_link_tamper_cannot_redirect_runner_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    poison: str,
) -> None:
    repo = _repository(tmp_path)
    index = Path(_git(repo, "rev-parse", "--git-path", "index"))
    if not index.is_absolute():
        index = repo / index
    index_before = index.read_bytes()
    objects_before = _git(repo, "count-objects", "-v")
    owner_before = process_runner.repository_fingerprint(repo)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv(
        "DRYDOCK_FAKE_POISON_GITDIR",
        "delete" if poison == "delete" else str(repo / ".git"),
    )
    with pytest.raises(
        process_runner.RunnerError, match=r"worktree \.git control"
    ):
        process_runner.mutate(
            repo,
            "try to redirect runner Git operations",
            "gpt-test",
            timeout=30,
            codex_prefix=_prefix(),
        )
    assert index.read_bytes() == index_before
    assert _git(repo, "count-objects", "-v") == objects_before
    assert process_runner.repository_fingerprint(repo) == owner_before


def test_worker_git_config_poison_is_detected_before_post_worker_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    config = repo / ".git" / "config"
    config_before = config.read_bytes()
    sentinel = tmp_path / "fsmonitor-invoked.txt"
    if os.name == "nt":
        fsmonitor = tmp_path / "hostile-fsmonitor.cmd"
        fsmonitor.write_text(
            f'@echo invoked>"{sentinel}"\r\n',
            encoding="utf-8",
        )
    else:
        fsmonitor = tmp_path / "hostile-fsmonitor"
        fsmonitor.write_text(
            f"#!/bin/sh\nprintf invoked > {str(sentinel)!r}\n",
            encoding="utf-8",
        )
        fsmonitor.chmod(0o755)
    hooks = tmp_path / "hostile-hooks"
    hooks.mkdir()
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_POISON_GIT_CONFIG", str(config))
    monkeypatch.setenv("DRYDOCK_FAKE_FSMONITOR", str(fsmonitor))
    monkeypatch.setenv("DRYDOCK_FAKE_HOOKS_PATH", str(hooks))
    try:
        with pytest.raises(
            process_runner.RunnerError,
            match="Git control surface changed",
        ):
            process_runner.mutate(
                repo,
                "poison trusted runner Git configuration",
                "gpt-test",
                timeout=30,
                codex_prefix=_prefix(),
            )
    finally:
        config.write_bytes(config_before)
    assert not sentinel.exists()


def test_worktree_git_pins_local_execution_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    boundary = process_runner._create_worktree(
        repo, "pin Git configuration", "HEAD"
    )
    observed: list[list[str]] = []
    original = process_runner._run_git

    def capture(
        cwd: Path,
        arguments: list[str],
        timeout: int = 60,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        observed.append(list(arguments))
        return original(cwd, arguments, timeout, **kwargs)

    monkeypatch.setattr(process_runner, "_run_git", capture)
    process_runner._run_worktree_git(
        boundary, ["status", "--porcelain=v1"]
    )
    call = observed[-1]
    configured = [
        call[index + 1]
        for index, value in enumerate(call)
        if value == "-c"
    ]
    assert configured == list(process_runner.WORKTREE_GIT_CONFIG_OVERRIDES)


def test_completed_worker_process_tree_is_quiesced_before_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_BACKGROUND", "1")
    result = process_runner.mutate(
        repo,
        "spawn a late writer that must not survive",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    late = Path(result["worktree"]) / "late-background.txt"
    time.sleep(2.5)
    assert not late.exists()
    assert "late-background.txt" not in result["changed_files"]


def test_ignored_worker_artifacts_are_reported_and_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_IGNORED", "1")
    result = process_runner.mutate(
        repo,
        "create an ignored artifact",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "ignored_artifacts"
    assert result["ignored_files"] == ["ignored-worker.txt"]
    assert "outside the review diff" in result["test_evidence"]["reason"]


@pytest.mark.parametrize(
    "path",
    [
        "Dockerfile",
        "Makefile",
        "script.sh",
        "script.ps1",
        "main.tf",
        "config.json",
        "module.mjs",
        "build.gradle",
    ],
)
def test_unknown_and_extensionless_changes_require_verification(
    path: str,
) -> None:
    gate = process_runner._test_applicability([path], [])
    assert gate["applicability"] == "applicable"
    assert gate["verdict"] == "blocked"


def test_inert_text_change_requires_review_and_is_never_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_TEXT", "1")
    result = process_runner.mutate(
        repo,
        "create a text-only review artifact",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "review_required"
    assert result["test_evidence"]["verdict"] == "not_applicable"
    assert result["test_evidence"]["trusted"] is False


def test_worker_attributes_change_invalidates_review_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_ATTRIBUTES", "1")
    with pytest.raises(
        process_runner.RunnerError, match=r"changed \.gitattributes"
    ):
        process_runner.mutate(
            repo,
            "try to suppress diff content",
            "gpt-test",
            timeout=30,
            codex_prefix=_prefix(),
        )


def test_snapshot_git_metadata_is_temporary_not_owner_owned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    index = Path(_git(repo, "rev-parse", "--git-path", "index"))
    if not index.is_absolute():
        index = repo / index
    index_before = index.read_bytes()
    objects_before = _git(repo, "count-objects", "-v")
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    process_runner.mutate(
        repo,
        "snapshot without changing Owner Git metadata",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert index.read_bytes() == index_before
    assert _git(repo, "count-objects", "-v") == objects_before


def test_mutation_with_no_changed_files_is_not_a_positive_result(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    result = process_runner.mutate(
        repo,
        "make a change that the fake intentionally omits",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "no_changes"
    assert result["changed_files"] == []
    assert result["test_evidence"]["verdict"] == "blocked"
    assert "not evidence" in result["test_evidence"]["reason"]
    assert result["merged"] is False


def test_mutation_rejects_owner_checkout_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_OWNER_PATH", str(repo / "outside.txt"))
    result = process_runner.mutate(
        repo,
        "attempt a contained change",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "owner_drift"
    assert result["owner_unchanged"] is False
    assert result["changed_files"] == []
    assert result["test_evidence"]["applicability"] == "not_evaluated"


def test_mutation_rejects_worker_owned_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_COMMIT", "1")
    with pytest.raises(
        process_runner.RunnerError,
        match="Git control surface changed",
    ):
        process_runner.mutate(
            repo,
            "try to commit from the worker",
            "gpt-test",
            timeout=30,
            codex_prefix=_prefix(),
        )


def test_verifier_fixes_read_only_root_and_binds_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    log = tmp_path / "verify-log.json"
    monkeypatch.setenv("DRYDOCK_FAKE_LOG", str(log))
    result = process_runner.verify(
        repo,
        "review the committed repository",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is (os.name == "nt")
    assert result["verdict"]["verdict"] == (
        "PASS" if os.name == "nt" else "BLOCKED"
    )
    assert result["tree_unchanged"] is True
    assert result["isolation"]["sandbox"] == "read-only"
    assert result["isolation"]["user_config_loaded_for_trust"] is True
    assert result["isolation"]["rules_loaded"] is False
    assert result["isolation"]["epistemic_independence"] is False
    assert (
        result["isolation"]["windows_job_descendant_lifetime_contained"]
        is (os.name == "nt")
    )

    call = json.loads(log.read_text(encoding="utf-8"))
    argv = call["argv"]
    assert argv[argv.index("-s") + 1] == "read-only"
    assert argv[argv.index("-C") + 1] == str(repo.resolve())
    assert "--output-schema" in argv
    assert "--output-last-message" in argv
    assert "danger-full-access" not in argv


def test_verifier_invalidates_pass_when_tree_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_OWNER_PATH", str(repo / "drift.txt"))
    result = process_runner.verify(
        repo,
        "review while an external actor changes the tree",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "tree_changed"
    assert result["tree_unchanged"] is False
    assert result["verdict"]["verdict"] == "BLOCKED"


def test_verifier_quiesces_background_descendants_before_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_BACKGROUND", "1")
    result = process_runner.verify(
        repo,
        "return a verdict and leave a late writer",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    time.sleep(2.5)
    assert result["ok"] is (os.name == "nt")
    assert result["tree_unchanged"] is True
    assert not (repo / "late-background.txt").exists()


@pytest.mark.parametrize("mode", ["bad_check", "bad_binding"])
def test_verifier_rejects_nested_schema_and_state_binding_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv(
        "DRYDOCK_FAKE_BAD_CHECK" if mode == "bad_check"
        else "DRYDOCK_FAKE_BAD_BINDING",
        "1",
    )
    result = process_runner.verify(
        repo,
        "return a malformed or stale verdict",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "invalid_verdict"
    assert result["verdict"] is None
    assert result["parse_error"]


def test_repository_fingerprint_fails_closed_when_untracked_bytes_exceed_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    (repo / "untracked.bin").write_bytes(b"too large")
    monkeypatch.setattr(process_runner, "MAX_FINGERPRINT_BYTES", 1)
    with pytest.raises(process_runner.RunnerError, match="byte bound"):
        process_runner.repository_fingerprint(repo)


def test_strict_json_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate JSON key"):
        process_runner._strict_json_loads('{"verdict":"PASS","verdict":"FAIL"}')


def test_cleanup_refuses_unrelated_branch_and_preserves_reviewable_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    result = process_runner.mutate(
        repo,
        "create reviewable work",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    with pytest.raises(process_runner.RunnerError, match="reserved prefix"):
        process_runner.cleanup_worktree(
            repo, Path(result["worktree"]), "feature/unrelated"
        )
    retained = process_runner.cleanup_worktree(
        repo, Path(result["worktree"]), result["branch"]
    )
    assert retained["ok"] is False
    assert retained["stage"] == "retained_reviewable_work"
    assert Path(result["worktree"]).exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction behavior")
def test_windows_junction_is_rejected_before_extract_and_cleanup(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    boundary = process_runner._create_worktree(
        repo, "junction containment", "HEAD"
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("must survive\n", encoding="utf-8")
    junction = boundary.path / "junction"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert created.returncode == 0, created.stderr
    try:
        with pytest.raises(process_runner.RunnerError, match="reparse"):
            process_runner._extract_changes(boundary)
        with pytest.raises(process_runner.RunnerError, match="reparse"):
            process_runner.cleanup_worktree(
                repo,
                boundary.path,
                boundary.branch,
                discard=True,
            )
        assert sentinel.read_text(encoding="utf-8") == "must survive\n"
    finally:
        if junction.exists():
            junction.rmdir()
    cleanup = process_runner.cleanup_worktree(
        repo,
        boundary.path,
        boundary.branch,
        discard=True,
    )
    assert cleanup["ok"] is True
    assert sentinel.read_text(encoding="utf-8") == "must survive\n"


def test_hardlink_is_rejected_before_extract_and_cleanup(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    boundary = process_runner._create_worktree(
        repo, "hardlink containment", "HEAD"
    )
    outside = tmp_path / "hardlink-target.txt"
    outside.write_text("must survive\n", encoding="utf-8")
    linked = boundary.path / "hardlink.txt"
    try:
        os.link(outside, linked)
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable on this filesystem: {exc}")
    try:
        with pytest.raises(process_runner.RunnerError, match="hardlink"):
            process_runner._extract_changes(boundary)
        with pytest.raises(process_runner.RunnerError, match="hardlink"):
            process_runner.cleanup_worktree(
                repo,
                boundary.path,
                boundary.branch,
                discard=True,
            )
        assert outside.read_text(encoding="utf-8") == "must survive\n"
    finally:
        if linked.exists():
            linked.unlink()
    cleanup = process_runner.cleanup_worktree(
        repo,
        boundary.path,
        boundary.branch,
        discard=True,
    )
    assert cleanup["ok"] is True
    assert outside.read_text(encoding="utf-8") == "must survive\n"


def test_worktree_boundary_scan_has_a_finite_entry_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    boundary = process_runner._create_worktree(
        repo, "bounded worktree scan", "HEAD"
    )
    original_scandir = process_runner.os.scandir
    next_calls = 0

    class BoundedScandir:
        def __init__(self, path: str | os.PathLike[str]) -> None:
            self.entries = original_scandir(path)

        def __enter__(self) -> "BoundedScandir":
            return self

        def __exit__(self, *args: object) -> None:
            self.entries.close()

        def __iter__(self) -> "BoundedScandir":
            return self

        def __next__(self) -> os.DirEntry[str]:
            nonlocal next_calls
            next_calls += 1
            if next_calls > 2:
                raise AssertionError("scanner consumed beyond its entry bound")
            return next(self.entries)

    try:
        monkeypatch.setattr(process_runner, "MAX_WORKTREE_ENTRIES", 1)
        monkeypatch.setattr(process_runner.os, "scandir", BoundedScandir)
        with pytest.raises(process_runner.RunnerError, match="entry bound"):
            process_runner._extract_changes(boundary)
        assert next_calls == 2
        next_calls = 0
        with pytest.raises(process_runner.RunnerError, match="entry bound"):
            process_runner.cleanup_worktree(
                repo,
                boundary.path,
                boundary.branch,
                discard=True,
            )
        assert next_calls == 2
    finally:
        monkeypatch.undo()
        cleanup = process_runner.cleanup_worktree(
            repo,
            boundary.path,
            boundary.branch,
            discard=True,
        )
        assert cleanup["ok"] is True


def test_timeout_is_never_green_and_retains_lease_only_if_process_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_SLEEP", "5")
    result = process_runner.mutate(
        repo,
        "bounded timeout test",
        "gpt-test",
        timeout=1,
        codex_prefix=_prefix(),
    )
    assert result["ok"] is False
    assert result["stage"] == "worker_timeout"
    assert result["worker"]["timed_out"] is True
    assert result["merged"] is False


def test_parallel_mutations_receive_distinct_worktrees_and_leases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_SLEEP", "0.2")

    def run(number: int) -> dict[str, object]:
        return process_runner.mutate(
            repo,
            f"parallel bounded task {number}",
            "gpt-test",
            timeout=30,
            codex_prefix=_prefix(),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, (1, 2)))
    assert len({result["worktree"] for result in results}) == 2
    assert len({result["branch"] for result in results}) == 2
    assert all(result["lease_released"] for result in results)
    assert all(result["merged"] is False for result in results)


def test_explicit_bounded_discard_removes_only_reserved_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    monkeypatch.setenv("DRYDOCK_FAKE_MUTATE", "1")
    result = process_runner.mutate(
        repo,
        "create disposable review work",
        "gpt-test",
        timeout=30,
        codex_prefix=_prefix(),
    )
    cleanup = process_runner.cleanup_worktree(
        repo,
        Path(result["worktree"]),
        result["branch"],
        discard=True,
    )
    assert cleanup["ok"] is True
    assert cleanup["removed"] is True
    assert cleanup["branch_removed"] is True
    assert not Path(result["worktree"]).exists()
    assert _git(repo, "status", "--porcelain") == ""


def test_orphan_cleanup_removes_only_stale_dead_reserved_lease(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    boundary = process_runner._create_worktree(repo, "orphan cleanup", "HEAD")
    worktree = boundary.path
    branch = boundary.branch
    lease_path = process_runner._lease_path(repo, worktree)
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "worktree": str(worktree),
                "branch": branch,
                "phase": "running",
                "process": {"pid": 99999999, "started": "gone"},
                "started_epoch": 0,
                "deadline_epoch": 0,
                "cleanup_grace_seconds": 1,
            }
        ),
        encoding="utf-8",
    )
    result = process_runner.cleanup_orphaned_leases(repo)
    assert result["ok"] is True
    assert result["cleaned"] == [
        {"lease": str(lease_path), "worktree": str(worktree), "branch": branch}
    ]
    assert not lease_path.exists()
    assert worktree.exists()


@pytest.mark.parametrize("deadline", ["NaN", "Infinity", "1e400"])
def test_non_finite_lease_deadline_never_reclaims(
    tmp_path: Path, deadline: str
) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    path = tmp_path / "lease.json"
    path.write_text(
        (
            '{"branch":"codex/drydock/test","cleanup_grace_seconds":1,'
            f'"deadline_epoch":{deadline},"phase":"running",'
            '"process":{"pid":99999999,"started":"gone"},'
            '"schema_version":1,"started_epoch":0,'
            f'"worktree":{json.dumps(str(worktree.resolve()))}}}'
        ),
        encoding="utf-8",
    )
    with pytest.raises(process_runner.RunnerError, match="unreadable"):
        process_runner.Lease.acquire(
            path,
            worktree,
            "codex/drydock/test",
            worker_timeout=30,
            cleanup_grace=10,
        )
    assert path.exists()
