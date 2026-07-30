"""The archive scan gate opens only on a proven pass.

Every other outcome -- offline, no run, still running, dirty worktree, no
remote, failed run -- blocks. An unverifiable scan is not a passed scan.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sdd  # noqa: E402


def _git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)


def _add_scan_workflow(repo: Path) -> None:
    workflow = repo / ".github" / "workflows" / f"{sdd.SCAN_WORKFLOW}.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("name: launchguardian\non: [push]\n", encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _add_scan_workflow(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    _git(tmp_path, "remote", "add", "origin", "git@github.com:owner/repo.git")
    return tmp_path


def test_project_without_the_workflow_is_not_blocked_but_is_disclosed(
    tmp_path: Path, monkeypatch
) -> None:
    """A project that never opted into scanning must not be blocked from
    archiving -- but 'not configured' must never be reported as a pass."""

    def boom(*_a, **_k):
        raise AssertionError("an unconfigured project must not be queried")

    monkeypatch.setattr(sdd.urllib.request, "urlopen", boom)
    _git(tmp_path, "init", "-q")
    state, detail = sdd.scan_gate(tmp_path)
    assert state == "not_configured"
    assert state != "passed"
    assert sdd.SCAN_WORKFLOW in detail
    assert sdd.scan_gate_blockers(tmp_path) == []


def test_removing_the_workflow_disables_the_gate_visibly(repo: Path, monkeypatch) -> None:
    """Deleting the workflow turns the gate off, which is why packet-guard
    governs CI config edits separately. Pinned so the trade-off stays explicit."""
    _stub_api(monkeypatch, {"workflow_runs": []})
    assert sdd.scan_gate_blockers(repo), "configured project with no run must block"
    (repo / ".github" / "workflows" / f"{sdd.SCAN_WORKFLOW}.yml").unlink()
    assert sdd.scan_gate(repo)[0] == "not_configured"
    assert sdd.scan_gate_blockers(repo) == []


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> bool:
        return False


def _stub_api(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    monkeypatch.setattr(
        sdd.urllib.request, "urlopen", lambda *a, **k: _Response(payload)
    )


def _run(name: str, status: str = "completed", conclusion: str = "success") -> dict:
    return {"name": name, "status": status, "conclusion": conclusion}


def test_successful_run_on_exact_head_passes(repo: Path, monkeypatch) -> None:
    _stub_api(monkeypatch, {"workflow_runs": [_run("launchguardian")]})
    state, _ = sdd.scan_gate(repo)
    assert state == "passed"
    assert sdd.scan_gate_blockers(repo) == []


def test_failed_run_blocks(repo: Path, monkeypatch) -> None:
    _stub_api(monkeypatch, {"workflow_runs": [_run("launchguardian", conclusion="failure")]})
    assert sdd.scan_gate(repo)[0] == "failed"
    assert sdd.scan_gate_blockers(repo)


def test_run_still_in_progress_blocks(repo: Path, monkeypatch) -> None:
    _stub_api(monkeypatch, {"workflow_runs": [_run("launchguardian", status="in_progress",
                                                   conclusion=None)]})
    state, detail = sdd.scan_gate(repo)
    assert state == "unverifiable"
    assert "still running" in detail


def test_no_run_for_this_commit_blocks(repo: Path, monkeypatch) -> None:
    _stub_api(monkeypatch, {"workflow_runs": []})
    state, detail = sdd.scan_gate(repo)
    assert state == "unverifiable"
    assert "no launchguardian run" in detail


def test_other_workflow_passing_does_not_count(repo: Path, monkeypatch) -> None:
    _stub_api(monkeypatch, {"workflow_runs": [_run("CI")]})
    assert sdd.scan_gate(repo)[0] == "unverifiable"


def test_offline_blocks_rather_than_crashes(repo: Path, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise OSError("network unreachable")

    monkeypatch.setattr(sdd.urllib.request, "urlopen", boom)
    state, detail = sdd.scan_gate(repo)
    assert state == "unverifiable"
    assert "could not be read" in detail


def test_dirty_worktree_blocks_before_any_network_call(repo: Path, monkeypatch) -> None:
    def boom(*_a, **_k):  # must never be reached
        raise AssertionError("network must not be consulted for a dirty tree")

    monkeypatch.setattr(sdd.urllib.request, "urlopen", boom)
    (repo / "dirty.py").write_text("y = 2\n", encoding="utf-8")
    state, detail = sdd.scan_gate(repo)
    assert state == "unverifiable"
    assert "uncommitted changes" in detail


def test_missing_github_remote_blocks(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _add_scan_workflow(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "c")
    state, detail = sdd.scan_gate(tmp_path)
    assert state == "unverifiable"
    assert "no GitHub origin remote" in detail


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("git@gitlab.com:owner/repo.git", None),
    ],
)
def test_remote_slug_parsing(tmp_path: Path, url: str, expected: str | None) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "remote", "add", "origin", url)
    assert sdd.github_slug(tmp_path) == expected


def test_environment_skip_is_recorded_as_unverifiable_not_passed(
    repo: Path, monkeypatch
) -> None:
    monkeypatch.setenv("DRYDOCK_SKIP_SCAN_GATE", "1")
    state, _ = sdd.scan_gate(repo)
    assert state == "unverifiable", "an opt-out must never read as a pass"
    assert sdd.scan_gate_blockers(repo)


def test_archive_readiness_stays_offline_and_pure(repo: Path, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise AssertionError("archive_readiness must never touch the network")

    monkeypatch.setattr(sdd.urllib.request, "urlopen", boom)
    change_dir = repo / "sdd-plus" / "changes" / "demo"
    change_dir.mkdir(parents=True)
    caps_dir = repo / "sdd-plus" / "specs" / "capabilities"
    caps_dir.mkdir(parents=True)
    sdd.archive_readiness(change_dir, caps_dir)
