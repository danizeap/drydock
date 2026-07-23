"""Tests for mutating delegation (`scripts/conductor/mutate.py`).

Uses real git worktrees in throwaway repos and a monkeypatched delegation (no real
Codex, no quota). Focus: the applicability-first gate, worktree isolation, the
no-merge guarantee, and cleanup safety.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import mutate as mutate_mod  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


def _g(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo(path):
    _g(["init"], path)
    _g(["config", "user.email", "t@example.com"], path)
    _g(["config", "user.name", "Test"], path)
    with open(os.path.join(path, "seed.txt"), "w") as f:
        f.write("seed\n")
    _g(["add", "-A"], path)
    _g(["commit", "-m", "seed"], path)


# ---- applicability-first gate (pure, security-critical) ----
def test_gate_docs_only_is_na_not_fail():
    g = mutate_mod.assess_gate(["README.md", "config.yaml"], None)
    assert g["applies"] is False and g["verdict"] == "n/a" and g["clears"] is True


def test_gate_code_green_clears():
    g = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": True})
    assert g["applies"] is True and g["verdict"] == "green" and g["clears"] is True


def test_gate_code_red_blocks():
    g = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": False})
    assert g["verdict"] == "red" and g["clears"] is False


def test_gate_code_without_tests_blocks():
    g = mutate_mod.assess_gate(["app.py"], None)
    assert g["verdict"] == "blocked" and g["clears"] is False


def test_gate_empty_change():
    g = mutate_mod.assess_gate([], None)
    assert g["verdict"] == "empty" and g["clears"] is False


def test_gate_mixed_code_and_docs_applies():
    # any code file present -> the test gate applies
    g = mutate_mod.assess_gate(["README.md", "app.py"], None)
    assert g["applies"] is True and g["clears"] is False


def test_gate_extensionless_code_basename_applies():
    # Dockerfile/Makefile carry no extension but are behavior-bearing -> gate applies
    for name in ("Dockerfile", "Makefile", "svc/Dockerfile"):
        g = mutate_mod.assess_gate([name], None)
        assert g["applies"] is True and g["verdict"] == "blocked", name


def test_create_worktree_structured_on_git_failure(monkeypatch, tmp_path):
    # git absent / spawn failure must yield a structured error, not a traceback
    def boom(*a, **k):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr(mutate_mod, "_git", boom)
    wt, branch, err = mutate_mod.create_worktree("HEAD", "task")
    assert wt is None and branch is None and "git worktree add failed" in err


# ---- worktree isolation + cleanup ----
def test_worktree_isolation_and_cleanup(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    wt, branch, err = mutate_mod.create_worktree("HEAD", "my task")
    assert wt and branch.startswith("codex/") and err is None
    with open(os.path.join(wt, "new.py"), "w") as f:
        f.write("x = 1\n")
    files, diff = mutate_mod.extract_changes(wt, "HEAD")
    assert "new.py" in files and "x = 1" in diff
    assert not os.path.exists(os.path.join(repo, "new.py"))  # main tree untouched
    mutate_mod.cleanup_worktree(wt, branch)
    assert not os.path.isdir(wt)
    assert "codex/" not in _g(["branch"], repo).stdout  # codex branch removed


def test_cleanup_never_deletes_non_codex_branch(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    _g(["branch", "important"], repo)
    wt, branch, _ = mutate_mod.create_worktree("HEAD", "x")
    mutate_mod.cleanup_worktree(wt, "important")   # spoofed non-codex branch name
    assert "important" in _g(["branch"], repo).stdout  # must survive
    _g(["branch", "-D", branch], repo)  # tidy the real codex branch


# ---- full mutate(): no merge, worktree kept, isolation ----
def _mutate_in(repo, monkeypatch, writer, **kw):
    monkeypatch.chdir(repo)
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda *a, **k: FAKE)
    monkeypatch.setattr(mutate_mod, "delegate_mutation", writer)
    return mutate_mod.mutate("do a thing", base="HEAD", **kw)


def test_mutate_does_not_merge_and_keeps_worktree(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)

    def writer(core, worktree, task, model, timeout_s=600):
        with open(os.path.join(worktree, "NOTES.md"), "w") as f:
            f.write("# note\n")
        return {"ok": True, "exit": 0, "usage": {"input_tokens": 1, "output_tokens": 1}}

    head_before = _g(["rev-parse", "HEAD"], repo).stdout.strip()
    out = _mutate_in(repo, monkeypatch, writer)
    try:
        assert out["ok"] is True and out["merged"] is False
        assert "NOTES.md" in out["files"]
        assert out["gate"]["verdict"] == "n/a" and out["clears_gate"] is True  # md -> n/a
        assert out["worktree"] and os.path.isdir(out["worktree"])              # kept for review
        assert _g(["rev-parse", "HEAD"], repo).stdout.strip() == head_before   # base not advanced
        assert not os.path.exists(os.path.join(repo, "NOTES.md"))              # main tree isolated
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])


def test_mutate_code_change_without_tests_blocks(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)

    def writer(core, worktree, task, model, timeout_s=600):
        with open(os.path.join(worktree, "feature.py"), "w") as f:
            f.write("def f():\n    return 1\n")
        return {"ok": True, "exit": 0, "usage": {}}

    out = _mutate_in(repo, monkeypatch, writer, test_cmd=None)
    try:
        assert out["gate"]["verdict"] == "blocked" and out["clears_gate"] is False
        assert out["worktree"] and os.path.isdir(out["worktree"])  # kept so Claude can inspect/fix
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])


def test_mutate_code_change_green_when_tests_pass(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)

    def writer(core, worktree, task, model, timeout_s=600):
        with open(os.path.join(worktree, "feature.py"), "w") as f:
            f.write("x = 1\n")
        return {"ok": True, "exit": 0, "usage": {}}

    # `git --version` always exits 0 -> stands in for a passing test command
    out = _mutate_in(repo, monkeypatch, writer, test_cmd="git --version")
    try:
        assert out["tests"]["ran"] is True and out["tests"]["pass"] is True
        assert out["gate"]["verdict"] == "green" and out["clears_gate"] is True
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])


def test_mutate_no_core(monkeypatch, tmp_path):
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda *a, **k: None)
    out = mutate_mod.mutate("x")
    assert out["ok"] is False and out["stage"] == "discover"
