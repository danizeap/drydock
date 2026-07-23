#!/usr/bin/env python3
"""Mutating delegation: Codex writes in an ISOLATED git worktree, gated before merge.

Codex gets its own worktree + `codex/…` branch with sandbox `workspace-write` — the
ONE place the conductor enables writes, confined to the worktree, never the Owner's
branch. The resulting diff passes an APPLICABILITY-FIRST gate (tests where they
apply; N/A is a clean pass, never a false fail). This module NEVER merges: it
returns a structured verdict + the diff + the worktree/branch for Claude to review
and merge deliberately. Every outcome is structured JSON.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # scripts/ -> `conductor` importable
from conductor import codex_bridge as cb  # noqa: E402

# Extensions whose change means "behavior changed" -> the test gate APPLIES.
_CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".go", ".rs",
             ".java", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs",
             ".swift", ".kt", ".scala", ".sh", ".ps1", ".sql", ".lua", ".r"}
# Behavior-bearing files that carry no extension.
_CODE_BASENAMES = {"dockerfile", "containerfile", "makefile", "rakefile", "gemfile",
                   "procfile", "jenkinsfile", "vagrantfile", "justfile", "brewfile"}


def _is_code_file(path):
    base = os.path.basename(path)
    if base.lower() in _CODE_BASENAMES:
        return True
    return os.path.splitext(path)[1].lower() in _CODE_EXT


def _git(args, cwd=None, timeout=60):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _slugify(s):
    keep = "".join(c if c.isalnum() or c in "-_" else "-" for c in (s or "").lower())
    return (keep.strip("-") or "task")[:40]


def create_worktree(base, task):
    """Create an isolated worktree + a fresh `codex/…` branch from `base`.
    Returns (worktree, branch, None) or (None, None, error) — never raises."""
    try:
        wt = tempfile.mkdtemp(prefix="drydock-codex-wt-")
    except OSError as e:
        return None, None, f"mkdtemp failed: {e}"
    branch = f"codex/{_slugify(task)}-{os.path.basename(wt)[-6:]}"
    try:
        r = _git(["worktree", "add", wt, "-b", branch, base])
    except (OSError, subprocess.SubprocessError) as e:  # git absent, timeout, etc.
        try:
            os.rmdir(wt)
        except OSError:
            pass
        return None, None, f"git worktree add failed: {e}"
    if r.returncode != 0:
        try:
            os.rmdir(wt)
        except OSError:
            pass
        return None, None, r.stderr.strip()
    return wt, branch, None


def cleanup_worktree(worktree, branch=None):
    """Remove a codex worktree and (ONLY) a `codex/` branch — never anything else."""
    if worktree and os.path.isdir(worktree):
        _git(["worktree", "remove", "--force", worktree])
    if worktree and not os.path.isdir(worktree) and branch and branch.startswith("codex/"):
        _git(["branch", "-D", branch])
    return True


def delegate_mutation(core, worktree, task, model, timeout_s=600):
    """Run Codex with sandbox=workspace-write, confined to `worktree`. This is the
    ONLY conductor path that enables writes; it never runs against the Owner's tree."""
    if not cb._SAFE_MODEL.match(model or ""):
        return {"ok": False, "stage": "bad_model", "error": repr(model)}
    argv = [*cb._as_prefix(core), "exec", "--json", "--skip-git-repo-check",
            "-s", "workspace-write", "-m", model, "-C", worktree]
    try:
        p = subprocess.run(argv, input=task, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"ok": False, "stage": "delegate_timeout"}
    except (OSError, ValueError) as e:
        return {"ok": False, "stage": "delegate_spawn", "error": str(e)}
    usage = None
    for ln in (p.stdout or "").splitlines():
        try:
            ev = json.loads(ln)
            if isinstance(ev, dict) and ev.get("type") == "turn.completed":
                usage = ev.get("usage")
        except Exception:
            pass
    return {"ok": p.returncode == 0, "exit": p.returncode, "usage": usage,
            "stderr_tail": (p.stderr or "")[-400:]}


def extract_changes(worktree, base):
    """Stage everything Codex produced in the worktree and diff it against base."""
    _git(["add", "-A"], cwd=worktree)
    names = _git(["diff", "--cached", "--name-only", base], cwd=worktree)
    files = [f for f in names.stdout.splitlines() if f.strip()]
    diff = _git(["diff", "--cached", base], cwd=worktree).stdout
    return files, diff


def run_tests(worktree, test_cmd, timeout_s=300):
    if not test_cmd:
        return None
    try:
        p = subprocess.run(test_cmd, cwd=worktree, shell=True, capture_output=True,
                           text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"ran": True, "pass": False, "output_tail": "test run timed out"}
    except Exception as e:  # noqa: BLE001
        return {"ran": False, "error": str(e)}
    return {"ran": True, "pass": p.returncode == 0,
            "output_tail": ((p.stdout or "") + (p.stderr or ""))[-800:]}


def assess_gate(files, test_result):
    """APPLICABILITY-FIRST gate. Decide 'does the test gate apply?' BEFORE pass/fail.
    N/A is a first-class clean pass, distinct from a FAIL. `clears` means the
    deterministic gate is satisfied — Claude's diff review is still required."""
    if not files:
        return {"applies": False, "verdict": "empty", "clears": False,
                "reason": "no changes produced"}
    code_changed = any(_is_code_file(f) for f in files)
    if not code_changed:
        return {"applies": False, "verdict": "n/a", "clears": True,
                "reason": "docs/config-only change — test gate does not apply"}
    if test_result is None or not test_result.get("ran"):
        return {"applies": True, "verdict": "blocked", "clears": False,
                "reason": "code changed but tests were not run"}
    if test_result.get("pass"):
        return {"applies": True, "verdict": "green", "clears": True,
                "reason": "code changed; tests pass"}
    return {"applies": True, "verdict": "red", "clears": False,
            "reason": "code changed; tests fail"}


def mutate(task, base="HEAD", test_cmd=None, weight="heavy", model=None, keep=True):
    core = cb.discover_core()
    if not core:
        return {"ok": False, "stage": "discover"}
    gauge = cb.summarize_gauge(cb.read_rate_limits(core))
    model = model or cb.route(weight, gauge)["model"]
    wt, branch, err = create_worktree(base, task)
    if not wt:
        return {"ok": False, "stage": "worktree", "error": err, "gauge": gauge}
    try:
        d = delegate_mutation(core, wt, task, model)
        files, diff = extract_changes(wt, base)
        tests = run_tests(wt, test_cmd)
        gate = assess_gate(files, tests)
        result = {"ok": True, "gauge": gauge, "model": model,
                  "worktree": wt, "branch": branch, "base": base,
                  "delegation": d, "files": files, "diff": diff,
                  "tests": tests, "gate": gate, "clears_gate": gate["clears"],
                  "merged": False,
                  "note": ("NOT merged. Review the diff, then merge deliberately. "
                           "Clearing the gate is necessary, not sufficient — Claude "
                           "must review scope/security/architecture before merge.")}
        if not keep or not files or not d.get("ok"):
            cleanup_worktree(wt, branch)
            result["worktree"] = None
            result["cleaned_up"] = True
        return result
    except Exception as e:  # noqa: BLE001
        cleanup_worktree(wt, branch)
        return {"ok": False, "stage": "mutate_error", "error": str(e), "gauge": gauge}


def main():
    ap = argparse.ArgumentParser(
        description="Delegate a MUTATING task to Codex in an isolated worktree (no auto-merge).")
    ap.add_argument("task", nargs="?", help="the implementation task for Codex")
    ap.add_argument("--base", default="HEAD", help="branch/commit to branch from")
    ap.add_argument("--test-cmd", default=None, help="test command to run in the worktree, e.g. 'pytest -q'")
    ap.add_argument("--weight", choices=["heavy", "light"], default="heavy")
    ap.add_argument("--model", default=None)
    ap.add_argument("--cleanup", nargs=2, metavar=("WORKTREE", "BRANCH"),
                    help="remove a worktree+branch from a prior run, then exit")
    args = ap.parse_args()
    if args.cleanup:
        cleanup_worktree(args.cleanup[0], args.cleanup[1])
        print(json.dumps({"ok": True, "cleaned_up": args.cleanup}))
        return 0
    if not args.task:
        ap.error("task is required unless --cleanup is used")
    out = mutate(args.task, args.base, args.test_cmd, args.weight, args.model)
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
