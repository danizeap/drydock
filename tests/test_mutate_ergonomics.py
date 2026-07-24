"""Field report #2 fixes for mutating delegation (`scripts/conductor/mutate.py`):
the fuel-resolution correction, unified `--files` caps, timeout scaling + partial
salvage, and worktree GC. No real Codex, no quota.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import mutate as mutate_mod  # noqa: E402
from conductor import review as review_mod  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


def _g(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo(path):
    _g(["init"], path)
    _g(["config", "user.email", "t@example.com"], path)
    _g(["config", "user.name", "Test"], path)
    with open(os.path.join(path, "seed.py"), "w") as f:
        f.write("x = 1\n")
    _g(["add", "-A"], path)
    _g(["commit", "-m", "seed"], path)


# ---- the headline: fuel gauge below its own resolution is null, not 0 ----

def test_below_resolution_fuel_is_null_not_zero():
    """Field report #2's #1 finding: a 181k-token task moved the weekly gauge by
    less than 1%, so it rounded to 0 and read as 'free'. Below-resolution is not
    zero — same absence-of-evidence-as-reassurance failure as the boolean gauge."""
    c = mutate_mod.summarize_cost({"input_tokens": 181184, "output_tokens": 963},
                                  {"used_percent": 10}, {"used_percent": 10})
    assert c["fuel_used_percent"] is None                  # NOT 0
    assert "resolution" in c["fuel_resolution"]
    assert c["total_tokens"] == 182147                     # tokens keep their resolution


def test_tokens_are_the_primary_signal_in_the_note():
    c = mutate_mod.summarize_cost({"input_tokens": 5, "output_tokens": 5},
                                  {"used_percent": 3}, {"used_percent": 3})
    assert "per-task cost" in c["note"] and "remaining_percent" in c["note"]


def test_reset_and_below_resolution_are_distinguished():
    reset = mutate_mod.summarize_cost({"input_tokens": 9}, {"used_percent": 90}, {"used_percent": 2})
    assert reset["fuel_used_percent"] is None and "reset" in reset["fuel_resolution"]
    sub = mutate_mod.summarize_cost({"input_tokens": 9}, {"used_percent": 5}, {"used_percent": 5})
    assert sub["fuel_used_percent"] is None and "resolution" in sub["fuel_resolution"]


def test_zero_delta_with_no_tokens_is_not_flagged_as_below_resolution():
    """A genuinely free no-op (no tokens) should not claim a sub-resolution cost."""
    c = mutate_mod.summarize_cost({}, {"used_percent": 7}, {"used_percent": 7})
    assert c["fuel_used_percent"] == 0 and c["fuel_resolution"] is None


# ---- N1: --files caps are unified with --diff, so they can't drift ----

def test_files_caps_match_the_diff_caps():
    """The 64KB per-file cap sat below a real 90KB source file and was asymmetric
    with --diff's 256KB. Sharing the constants kills the asymmetry permanently."""
    assert mutate_mod.MAX_INLINE_FILE_BYTES == review_mod.MAX_FILE_BYTES == 256 * 1024
    assert mutate_mod.MAX_INLINE_BYTES == review_mod.MAX_TOTAL_BYTES == 512 * 1024


def test_a_ninety_kb_file_is_now_scopable(tmp_path):
    """The exact file that failed in the field: tools.ts at 90,614 bytes."""
    p = os.path.join(str(tmp_path), "tools.ts")
    with open(p, "w") as f:
        f.write("x".ljust(90_614))
    prompt, err = mutate_mod.build_scoped_task("edit it", str(tmp_path), ["tools.ts"])
    assert err is None and prompt is not None       # previously blocked at 64KB


# ---- N4: timeout scaling + operator lever ----

def test_timeout_is_clamped_to_a_sane_range():
    assert mutate_mod._clamp_timeout(None) == mutate_mod.DEFAULT_MUTATE_TIMEOUT
    assert mutate_mod._clamp_timeout(30) == 60                       # floor
    assert mutate_mod._clamp_timeout(99999) == mutate_mod.MAX_MUTATE_TIMEOUT
    assert mutate_mod._clamp_timeout(1200) == 1200
    assert mutate_mod.DEFAULT_MUTATE_TIMEOUT == 900                  # raised from 600


def test_operator_timeout_is_passed_through(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda *a, **k: FAKE)
    seen = {}

    def writer(core, worktree, task, model, timeout_s=None):
        seen["t"] = timeout_s
        return {"ok": True, "exit": 0, "usage": {"input_tokens": 1, "output_tokens": 1}}

    monkeypatch.setattr(mutate_mod, "delegate_mutation", writer)
    out = mutate_mod.mutate("do a thing", base="HEAD", timeout=1500)
    try:
        assert seen["t"] == 1500
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])


# ---- N2: a timed-out run keeps its partial work ----

def test_timeout_keeps_the_partial_work_and_never_clears(monkeypatch, tmp_path):
    """The reported failure: a timed-out sweep's 100 insertions were deleted with
    the worktree. Now the tree is kept, flagged partial, and cannot clear the gate."""
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda *a, **k: FAKE)

    def timed_out_writer(core, worktree, task, model, timeout_s=None):
        # Codex wrote real work before the kill:
        with open(os.path.join(worktree, "seed.py"), "a") as f:
            f.write("y = 2\ndef added(): return 3\n")
        return {"ok": False, "stage": "delegate_timeout", "partial": True,
                "timeout_s": timeout_s, "usage": {"input_tokens": 50, "output_tokens": 10}}

    monkeypatch.setattr(mutate_mod, "delegate_mutation", timed_out_writer)
    out = mutate_mod.mutate("sweep the file", base="HEAD", test_cmd=None)
    try:
        assert out["partial"] is True
        assert out["worktree"] and os.path.isdir(out["worktree"])   # NOT deleted
        assert "seed.py" in out["files"] and out["diff"].strip()    # the salvage
        assert out["clears_gate"] is False                          # incomplete never clears
        assert "INCOMPLETE" in out["note"]
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])


def test_timeout_that_wrote_nothing_is_cleaned_up(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda *a, **k: FAKE)

    def empty_timeout(core, worktree, task, model, timeout_s=None):
        return {"ok": False, "stage": "delegate_timeout", "partial": True, "usage": None}

    monkeypatch.setattr(mutate_mod, "delegate_mutation", empty_timeout)
    out = mutate_mod.mutate("do a thing", base="HEAD")
    assert out["partial"] is False and out.get("cleaned_up") is True  # nothing to salvage


def test_delegate_timeout_captures_partial_usage(monkeypatch):
    """The subprocess populates stdout before the kill, so a usage read survives."""
    import subprocess as sp

    def fake_run(*a, **k):
        raise sp.TimeoutExpired(
            cmd="codex", timeout=k.get("timeout"),
            output='{"type":"turn.completed","usage":{"input_tokens":7}}\n', stderr="")

    monkeypatch.setattr(mutate_mod.subprocess, "run", fake_run)
    d = mutate_mod.delegate_mutation(["codex"], "/tmp/wt", "task", mutate_mod.cb.FLAGSHIP, timeout_s=5)
    assert d["stage"] == "delegate_timeout" and d["partial"] is True
    assert d["usage"] == {"input_tokens": 7} and d["timeout_s"] == 5


# ---- N3: worktree GC removes empty orphans, keeps work ----

def test_gc_removes_empty_orphans_but_keeps_work(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    empty_wt = str(tmp_path / "empty_wt")
    work_wt = str(tmp_path / "work_wt")
    _g(["worktree", "add", empty_wt, "-b", "codex/empty", "HEAD"], repo)
    _g(["worktree", "add", work_wt, "-b", "codex/haswork", "HEAD"], repo)
    with open(os.path.join(work_wt, "new.py"), "w") as f:   # uncommitted work
        f.write("salvage me\n")

    out = mutate_mod.gc_worktrees()
    removed = {r["branch"] for r in out["removed"]}
    kept = {k["branch"] for k in out["kept_with_work"]}
    assert "codex/empty" in removed and not os.path.isdir(empty_wt)
    assert "codex/haswork" in kept and os.path.isdir(work_wt)       # work preserved
    mutate_mod.cleanup_worktree(work_wt, "codex/haswork")


def test_gc_keeps_a_codex_worktree_holding_COMMITTED_work(monkeypatch, tmp_path):
    """Verifier Finding 1: `git status` sees only uncommitted work, so a codex
    worktree that COMMITTED its changes read as empty and was force-deleted, its
    commits left dangling. 'no uncommitted changes' is not 'no work'."""
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    wt = str(tmp_path / "committed_wt")
    _g(["worktree", "add", wt, "-b", "codex/committed", "HEAD"], repo)
    with open(os.path.join(wt, "work.py"), "w") as f:
        f.write("real = 1\n")
    _g(["add", "-A"], wt)
    _g(["commit", "-m", "codex committed work"], wt)   # clean tree, real work

    out = mutate_mod.gc_worktrees()
    assert any(k["branch"] == "codex/committed" for k in out["kept_with_work"])
    assert all(r["branch"] != "codex/committed" for r in out["removed"])
    assert os.path.isdir(wt)                           # NOT destroyed
    mutate_mod.cleanup_worktree(wt, "codex/committed")


def test_gc_fails_safe_and_keeps_when_the_work_check_errors(monkeypatch):
    """On any doubt, keep — never destroy salvage on a failed probe (the N2 lesson)."""
    class _Err:
        returncode, stdout, stderr = 1, "", "boom"

    monkeypatch.setattr(mutate_mod, "_git", lambda *a, **k: _Err())
    assert mutate_mod._worktree_has_work("/any/path") is True   # errored probe -> keep


def test_gc_never_touches_a_non_codex_worktree(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    mine = str(tmp_path / "my_wt")
    _g(["worktree", "add", mine, "-b", "feature/mine", "HEAD"], repo)   # not codex/
    out = mutate_mod.gc_worktrees()
    assert all("feature/mine" not in r["branch"] for r in out["removed"])
    assert os.path.isdir(mine)                                       # untouched
    _g(["worktree", "remove", "--force", mine], repo)


def test_gc_dry_run_removes_nothing(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    wt = str(tmp_path / "empty_wt")
    _g(["worktree", "add", wt, "-b", "codex/empty", "HEAD"], repo)
    out = mutate_mod.gc_worktrees(dry_run=True)
    assert out["dry_run"] is True
    assert any(r["branch"] == "codex/empty" for r in out["removed"])
    assert os.path.isdir(wt)                                         # reported, not removed
    _g(["worktree", "remove", "--force", wt], repo)
