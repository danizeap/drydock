"""Tests for mutating delegation (`scripts/conductor/mutate.py`).

Uses real git worktrees in throwaway repos and a monkeypatched delegation (no real
Codex, no quota). Focus: the applicability-first gate, worktree isolation, the
no-merge guarantee, and cleanup safety.
"""
import json
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import mutate as mutate_mod  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


def _prepared_fake_sandbox():
    return mutate_mod.prepare_test_sandbox(FAKE)


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
    # `&&` is compiled into sequential argv; quoted text stays one argument.
    for cmd in ("pytest -q", "pytest && npm run lint", 'pytest -k "a and b"'):
        assert mutate_mod._has_shell_masking(cmd) is False, cmd


def test_redirects_are_refused_instead_of_executed():
    for cmd in ("pytest 2>&1", "pytest > result.txt", "pytest < input.txt"):
        assert mutate_mod._has_shell_masking(cmd) is True, cmd


def test_single_quote_is_not_a_quote_on_windows():
    # cmd.exe does not quote with `'`, so `'a|b'` IS a real pipeline there
    assert mutate_mod._has_shell_masking("pytest 'a|b'") is (os.name == "nt")


def test_runner_delegation_is_disclosed_not_blocked(tmp_path):
    # A package runner may mask failures internally. The advisory is retained
    # even though implicit shell execution is removed.
    note = mutate_mod._runner_note([["npm", "run", "test:ci"]])
    r = {
        "ran": True,
        "pass": True,
        "exit_code_trusted": True,
        "runner_note": note,
    }
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
    assert r["ran"] is False
    assert "sequencing" in r["trust_reason"]  # actual refusal, not "pipe" only
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
    piped = mutate_mod.run_tests(str(tmp_path), "python -c pass | more")
    assert piped["ran"] is False and piped["exit_code_trusted"] is False
    plain = mutate_mod.run_tests(
        str(tmp_path),
        [os.path.basename(sys.executable), "-c", "pass"],
        sandbox=_prepared_fake_sandbox(),
    )
    assert plain["exit_code_trusted"] is True and plain["pass"] is True


def test_run_tests_detects_missing_node_modules(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    r = mutate_mod.run_tests(
        str(tmp_path),
        [os.path.basename(sys.executable), "-c", "pass"],
        sandbox=_prepared_fake_sandbox(),
    )
    assert r["env_warning"] and "node_modules" in r["env_warning"]


def test_run_tests_refuses_direct_controller_execution(tmp_path):
    plan = mutate_mod.compile_test_plan(
        [os.path.basename(sys.executable), "-c", "pass"]
    )
    result = mutate_mod.run_tests(str(tmp_path), plan)
    assert result["ran"] is False
    assert result["exit_code_trusted"] is False
    assert "prepared Codex test sandbox is required" in result["error"]
    assert result["sandbox"] is None


def test_readiness_timeout_reports_process_tree_cleanup(monkeypatch):
    cleanup = {
        "attempted": True,
        "mechanism": "test process tree",
        "confirmed": False,
    }

    def fake_timeout(_argv, _worktree, _timeout_s):
        return None, "bounded probe output", cleanup

    monkeypatch.setattr(mutate_mod, "_run_test_step", fake_timeout)
    with pytest.raises(
        mutate_mod.TestPlanError,
        match="process-tree cleanup unconfirmed",
    ):
        mutate_mod.prepare_test_sandbox(FAKE, timeout_s=1)


def test_run_tests_wraps_absolute_argv_in_network_disabled_sandbox(
    tmp_path, monkeypatch
):
    plan = mutate_mod.compile_test_plan(["git", "--version"])
    sandbox = _prepared_fake_sandbox()
    observed = []

    def fake_run(argv, worktree, timeout_s):
        observed.append((argv, worktree, timeout_s))
        return (
            subprocess.CompletedProcess(argv, 0, "git version fake", ""),
            None,
            None,
        )

    monkeypatch.setattr(mutate_mod, "_run_test_step", fake_run)
    result = mutate_mod.run_tests(
        str(tmp_path),
        plan,
        sandbox=sandbox,
    )

    assert result["pass"] is True
    assert result["sandbox"]["mechanism"] == "codex sandbox permission profile"
    assert result["sandbox"]["requested_direct_network"] == "disabled"
    assert result["sandbox"]["requested_write_scope"] == os.path.realpath(
        str(tmp_path)
    )
    assert result["sandbox"]["per_run_boundary_verification"] == "not performed"
    assert result["sandbox"]["host_read_isolation"] == "not established"
    assert "direct_network" not in result["sandbox"]
    assert "write_scope" not in result["sandbox"]
    assert "test-created files may remain unstaged" in result["post_test_worktree"]
    argv, observed_worktree, observed_timeout = observed[0]
    assert argv[: len(sandbox.prefix)] == list(sandbox.prefix)
    assert argv[len(sandbox.prefix)] == "sandbox"
    assert "--sandbox-state-disable-network" in argv
    assert "--include-managed-config" in argv
    assert argv[-len(plan.steps[0]):] == list(plan.steps[0])
    assert observed_worktree == str(tmp_path)
    assert observed_timeout > 0
    configs = [argv[index + 1] for index, item in enumerate(argv) if item == "-c"]
    assert any("network.enabled=false" in item for item in configs)
    assert any("ignore_default_excludes=false" in item for item in configs)
    if os.name == "nt":
        assert "windows.sandbox='elevated'" in configs
    encoded_root = mutate_mod._toml_basic_string(os.path.realpath(str(tmp_path)))
    assert any(encoded_root in item for item in configs)


def test_structured_test_plan_resolves_absolute_executable_before_run():
    plan = mutate_mod.compile_test_plan(
        [os.path.basename(sys.executable), "-c", "pass"]
    )
    assert plan is not None
    assert len(plan.steps) == 1
    assert os.path.isabs(plan.steps[0][0])
    assert os.path.isfile(plan.steps[0][0])


def test_legacy_and_chain_compiles_to_sequential_steps():
    plan = mutate_mod.compile_test_plan("git --version && git --version")
    assert plan is not None
    assert len(plan.steps) == 2
    assert all(os.path.isabs(step[0]) for step in plan.steps)


@pytest.mark.parametrize(
    "command",
    [
        "git --version | more",
        "git --version ; echo done",
        "git --version & echo done",
        "git --version || echo done",
        "git --version > result.txt",
        "git --version\nwhoami",
        "echo $(whoami)",
        'echo "$(whoami)"',
        'echo "`whoami`"',
        'git --version "unterminated',
    ],
)
def test_unsafe_legacy_test_plan_is_rejected(command):
    with pytest.raises(mutate_mod.TestPlanError):
        mutate_mod.compile_test_plan(command)


@pytest.mark.parametrize(
    "argv",
    [
        ["bash", "-c", "true"],
        ["sh", "-c", "true"],
        ["cmd", "/c", "exit 0"],
        ["powershell", "-Command", "exit 0"],
        ["pwsh", "-Command", "exit 0"],
    ],
)
def test_explicit_shell_test_steps_are_rejected(argv):
    with pytest.raises(mutate_mod.TestPlanError, match="shell launcher"):
        mutate_mod.compile_test_plan(argv)


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["env", "sh", "-c", "true"], "env"),
        (["xargs", "sh", "-c", "true"], "xargs"),
        (["nice", "sh", "-c", "true"], "nice"),
        (["timeout", "5", "sh", "-c", "true"], "timeout"),
        (["nohup", "sh", "-c", "true"], "nohup"),
        (["stdbuf", "-o0", "sh", "-c", "true"], "stdbuf"),
        (["setsid", "sh", "-c", "true"], "setsid"),
        (["script", "-c", "sh -c true"], "script"),
        (["busybox", "sh", "-c", "true"], "busybox"),
        (["doskey", "macro=sh -c true"], "doskey"),
        (["perl", "-e", "system 'sh -c true'"], "perl"),
        (["python", "-c", "import os; os.system('sh -c true')"], "python"),
        (["node", "-e", "require('child_process').execSync('sh -c true')"], "node"),
    ],
)
def test_transitive_shell_launchers_are_allowed_but_disclosed(
    monkeypatch, argv, expected
):
    monkeypatch.setattr(
        mutate_mod,
        "_resolve_test_executable",
        lambda _name: os.path.realpath(sys.executable),
    )
    plan = mutate_mod.compile_test_plan(argv)
    note = mutate_mod._runner_note(plan.requested_steps)
    assert plan is not None
    assert note is not None
    assert repr(expected) in note
    assert "cannot prove what that project runner executes internally" in note


def test_windows_batch_shim_is_rejected_even_without_shell_flag(monkeypatch):
    monkeypatch.setattr(
        mutate_mod,
        "_resolve_test_executable",
        lambda _name: r"C:\trusted\npm.cmd",
    )
    with pytest.raises(mutate_mod.TestPlanError, match="batch/command shim"):
        mutate_mod.compile_test_plan(["npm", "test"])


def test_structured_plan_short_circuits_after_first_failure(tmp_path):
    executable = os.path.basename(sys.executable)
    sentinel = tmp_path / "must-not-exist.txt"
    plan = mutate_mod.compile_test_plan(
        [
            [executable, "-c", "raise SystemExit(7)"],
            [
                executable,
                "-c",
                f"open({str(sentinel)!r}, 'w').write('unsafe')",
            ],
        ]
    )
    result = mutate_mod.run_tests(
        str(tmp_path),
        plan,
        sandbox=_prepared_fake_sandbox(),
    )
    assert result["ran"] is True
    assert result["pass"] is False
    assert result["steps_completed"] == 1
    assert not sentinel.exists()


def test_structured_plan_uses_one_total_timeout_budget(
    tmp_path, monkeypatch
):
    plan = mutate_mod.compile_test_plan(
        [["git", "--version"], ["git", "--version"]]
    )
    clock = iter((0.0, 0.0, 100.0))
    observed_timeouts = []
    sandbox = _prepared_fake_sandbox()

    def fake_run(_argv, _worktree, timeout_s):
        observed_timeouts.append(timeout_s)
        return subprocess.CompletedProcess([], 0, "ok", ""), None, None

    monkeypatch.setattr(mutate_mod.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(mutate_mod, "_run_test_step", fake_run)
    result = mutate_mod.run_tests(
        str(tmp_path),
        plan,
        timeout_s=300,
        sandbox=sandbox,
    )
    assert result["pass"] is True
    assert observed_timeouts == [300.0, 200.0]


def test_timed_out_test_reaps_descendant_and_reports_cleanup(tmp_path):
    spawned = tmp_path / "descendant-spawned.txt"
    orphan = tmp_path / "orphan-survived.txt"
    child_code = (
        "import pathlib,time;"
        "time.sleep(2.5);"
        f"pathlib.Path({str(orphan)!r}).write_text("
        "'survived', encoding='utf-8')"
    )
    parent_code = (
        "import pathlib,subprocess,sys,time;"
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]);"
        f"pathlib.Path({str(spawned)!r}).write_text("
        "'spawned', encoding='utf-8');"
        "time.sleep(30)"
    )
    plan = mutate_mod.compile_test_plan(
        [os.path.basename(sys.executable), "-c", parent_code]
    )

    result = mutate_mod.run_tests(
        str(tmp_path),
        plan,
        timeout_s=1.5,
        sandbox=_prepared_fake_sandbox(),
    )

    assert result["ran"] is True
    assert result["pass"] is False
    assert result["timeout_cleanup"]["attempted"] is True
    assert result["timeout_cleanup"]["mechanism"]
    assert result["timeout_cleanup"]["direct_process_stopped"] is True
    assert result["timeout_cleanup"]["escaped_descendants"] == "not ruled out"
    assert spawned.exists(), "the timeout fired before the descendant was spawned"
    time.sleep(3)
    assert not orphan.exists()


def test_worktree_planted_executable_cannot_win_search(tmp_path):
    plan = mutate_mod.compile_test_plan(["git", "--version"])
    planted = tmp_path / os.path.basename(plan.steps[0][0])
    planted.write_text("not the trusted executable", encoding="utf-8")
    result = mutate_mod.run_tests(
        str(tmp_path),
        plan,
        sandbox=_prepared_fake_sandbox(),
    )
    assert result["ran"] is True
    assert result["pass"] is True
    assert "git version" in result["output_tail"].lower()


def test_executable_from_worker_writable_temp_path_is_refused(
    tmp_path, monkeypatch
):
    executable = tmp_path / ("runner.exe" if os.name == "nt" else "runner")
    executable.write_bytes(b"not trusted")
    monkeypatch.setenv("PATH", str(tmp_path))
    if os.name == "nt":
        monkeypatch.setenv("PATHEXT", ".EXE")
    with pytest.raises(mutate_mod.TestPlanError, match="mutating worker"):
        mutate_mod.compile_test_plan(["runner"])


def test_test_plan_refuses_paths_and_plan_overflow():
    with pytest.raises(mutate_mod.TestPlanError, match="bare executable"):
        mutate_mod.compile_test_plan([sys.executable, "-c", "pass"])
    with pytest.raises(mutate_mod.TestPlanError, match="exceeds 8 steps"):
        mutate_mod.compile_test_plan([["git", "--version"]] * 9)
    with pytest.raises(mutate_mod.TestPlanError, match="character bound"):
        mutate_mod.compile_test_plan(
            [["git", *("x" * mutate_mod.MAX_TEST_ARG_CHARS for _ in range(4))]]
        )


def test_forged_compiled_plan_is_revalidated_before_execution():
    forged_shell = mutate_mod.TestPlan(
        [["cmd.exe", "/c", "whoami"]],
        [["cmd", "/c", "whoami"]],
        "structured-argv",
    )
    with pytest.raises(mutate_mod.TestPlanError):
        mutate_mod.compile_test_plan(forged_shell)

    real = mutate_mod.compile_test_plan(["git", "--version"])
    forged_relative = mutate_mod.TestPlan(
        [["git", "--version"]],
        real.requested_steps,
        real.source,
    )
    with pytest.raises(mutate_mod.TestPlanError, match="does not match"):
        mutate_mod.compile_test_plan(forged_relative)


def test_invalid_plan_blocks_before_codex_discovery_or_worktree(
    monkeypatch,
):
    def should_not_run(*_args, **_kwargs):
        raise AssertionError("invalid plan reached Codex discovery")

    monkeypatch.setattr(mutate_mod.cb, "discover_core", should_not_run)
    result = mutate_mod.mutate("bounded task", test_cmd="pytest | more")
    assert result["ok"] is False
    assert result["stage"] == "test_plan"


def test_unavailable_test_sandbox_blocks_before_worktree_or_worker(
    monkeypatch,
):
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda: FAKE)

    def unavailable(*_args, **_kwargs):
        raise mutate_mod.TestPlanError("sandbox unavailable")

    def should_not_run(*_args, **_kwargs):
        raise AssertionError("sandbox failure reached worktree or worker")

    monkeypatch.setattr(mutate_mod, "prepare_test_sandbox", unavailable)
    monkeypatch.setattr(mutate_mod, "create_worktree", should_not_run)
    monkeypatch.setattr(mutate_mod, "delegate_mutation", should_not_run)
    result = mutate_mod.mutate("bounded task", test_cmd="git --version")
    assert result["ok"] is False
    assert result["stage"] == "test_sandbox"
    assert "sandbox unavailable" in result["error"]


def test_test_argv_json_accepts_one_or_many_steps():
    one = mutate_mod.decode_test_argv_json('["python", "-m", "pytest"]')
    many = mutate_mod.decode_test_argv_json(
        '[["python", "-m", "pytest"], ["git", "diff", "--check"]]'
    )
    assert one == ["python", "-m", "pytest"]
    assert len(many) == 2


def test_test_argv_json_rejects_malformed_or_wrong_shape():
    for raw in ("not-json", '{"command":"pytest"}', "[]"):
        with pytest.raises(mutate_mod.TestPlanError):
            mutate_mod.decode_test_argv_json(raw)


def test_cli_invalid_json_is_structured_and_never_reaches_codex():
    script = os.path.join(ROOT, "scripts", "conductor", "mutate.py")
    process = subprocess.run(
        [
            sys.executable,
            script,
            "bounded task",
            "--test-argv-json",
            "not-json",
        ],
        capture_output=True,
        text=True,
    )
    result = json.loads(process.stdout)
    assert process.returncode == 1
    assert process.stderr == ""
    assert result["ok"] is False
    assert result["stage"] == "test_plan"


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
