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
    g = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": True, "exit_code_trusted": True})
    assert g["applies"] is True and g["verdict"] == "green" and g["clears"] is True


def test_gate_code_red_blocks():
    g = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": False, "exit_code_trusted": True})
    assert g["verdict"] == "red" and g["clears"] is False


def test_gate_defaults_to_untrusted_when_key_absent():
    # fail-CLOSED: a result that does not assert its own trust is not trusted.
    g = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": True})
    assert g["verdict"] == "unverifiable" and g["clears"] is False


def test_masking_shell_forms_are_untrusted():
    # every construct that can decouple the shell's status from the test's
    for cmd in ("pytest | tail", "pytest ; echo done", "pytest & echo done",
                "pytest || true", "pytest\necho done", "echo `pytest`", "echo $(pytest)"):
        assert mutate_mod._has_shell_masking(cmd) is True, cmd


def test_safe_shell_forms_stay_trusted():
    # `&&` propagates failure; `2>&1` is a redirect, not a separator
    for cmd in ("pytest -q", "pytest && npm run lint", "pytest 2>&1", 'pytest -k "a and b"'):
        assert mutate_mod._has_shell_masking(cmd) is False, cmd


def test_single_quote_is_not_a_quote_on_windows():
    # cmd.exe does not quote with `'`, so `'a|b'` IS a real pipeline there
    assert mutate_mod._has_shell_masking("pytest 'a|b'") is (os.name == "nt")


def test_runner_delegation_is_disclosed_not_blocked(tmp_path):
    # The gate can only judge the top-level command's SHAPE. `npm run ci` may pipe
    # internally where we cannot see — disclose it as an advisory, never block.
    r = mutate_mod.run_tests(str(tmp_path), "npm run test:ci")
    assert r["exit_code_trusted"] is True          # shape is simple -> still trusted
    assert r["runner_note"] and "npm run" in r["runner_note"]
    g = mutate_mod.assess_gate(["app.py", "tests/test_app.py"], r)
    assert any("delegates to" in a for a in g["advisories"])
    assert g["clears"] is (g["verdict"] == "green")  # advisory did not gate


def test_detects_common_runners():
    for cmd, expected in [("npm run ci", "npm run"), ("npm test", "npm test"),
                          ("make test", "make"), ("bash -c 'x'", "bash"),
                          ("yarn verify", "yarn")]:
        assert mutate_mod._delegates_to_runner(cmd) == expected, cmd
    for cmd in ("pytest -q", "npx vitest run", "cargo test"):
        assert mutate_mod._delegates_to_runner(cmd) is None, cmd


def test_unverifiable_reason_names_actual_cause(tmp_path):
    r = mutate_mod.run_tests(str(tmp_path), "exit 1 ; echo done")
    g = mutate_mod.assess_gate(["app.py"], r)
    assert g["verdict"] == "unverifiable"
    assert "';'" in g["reason"] or "simple" in g["reason"]   # not "pipe" only
    g2 = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": True})
    assert "did not assert a trustworthy exit code" in g2["reason"]


def test_looks_like_test_is_precise():
    for p in ("tests/test_a.py", "src/foo.test.ts", "spec/foo_spec.rb",
              "a/__tests__/b.js", "test_x.py"):
        assert mutate_mod._looks_like_test(p), p
    for p in ("src/latest.py", "src/inspector.py", "lib/contest.ts", "src/greatest.go"):
        assert not mutate_mod._looks_like_test(p), p


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


def test_gate_refuses_green_on_untrusted_exit_code():
    # field-report 6.1: a shell pipe masks the real exit code -> NEVER green.
    g = mutate_mod.assess_gate(["app.py"], {"ran": True, "pass": True, "exit_code_trusted": False})
    assert g["verdict"] == "unverifiable" and g["clears"] is False


def test_gate_refuses_green_when_test_env_broken():
    # field-report 6.2: a green from a worktree with no deps is meaningless.
    g = mutate_mod.assess_gate(["app.ts"], {"ran": True, "pass": True, "exit_code_trusted": True,
                                            "env_warning": "no node_modules"})
    assert g["verdict"] == "unverifiable" and g["clears"] is False


def test_run_tests_flags_piped_and_trusts_plain(tmp_path):
    piped = mutate_mod.run_tests(str(tmp_path), "exit 1 | cat")
    assert piped["ran"] is True and piped["exit_code_trusted"] is False
    plain = mutate_mod.run_tests(str(tmp_path), "exit 0")
    assert plain["exit_code_trusted"] is True and plain["pass"] is True


def test_run_tests_detects_missing_node_modules(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    r = mutate_mod.run_tests(str(tmp_path), "exit 0")
    assert r["env_warning"] and "node_modules" in r["env_warning"]


def test_gate_coverage_gap_advisory():
    # field-report 6.4: new code with no test file in the diff -> advisory (not a fail).
    ok = {"ran": True, "pass": True, "exit_code_trusted": True}
    g = mutate_mod.assess_gate(["app.py"], ok)
    assert g["verdict"] == "green" and any("no test file" in a for a in g["advisories"])
    g2 = mutate_mod.assess_gate(["app.py", "tests/test_app.py"], ok)
    assert g2["advisories"] == []


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
