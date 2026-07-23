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
             ".swift", ".kt", ".scala", ".sh", ".ps1", ".sql", ".lua", ".r",
             ".vue", ".svelte", ".dart", ".ex", ".exs", ".prisma"}
# Behavior-bearing files that carry no extension.
_CODE_BASENAMES = {"dockerfile", "containerfile", "makefile", "rakefile", "gemfile",
                   "procfile", "jenkinsfile", "vagrantfile", "justfile", "brewfile"}


def _is_code_file(path):
    base = os.path.basename(path)
    if base.lower() in _CODE_BASENAMES:
        return True
    return os.path.splitext(path)[1].lower() in _CODE_EXT


_RUNNER_FIRST = {"make", "bash", "sh", "cmd", "powershell", "pwsh", "yarn", "pnpm"}


def _delegates_to_runner(cmd):
    """Name the script-runner a command delegates to, if any.

    The allow-list can only judge the SHAPE of the top-level command. If that
    command hands off to a runner (`npm run ci`, `make test`, `bash -c '…'`), any
    masking inside that script is invisible to us — `bash -c "false; true"` is a
    genuinely simple command that exits 0. We cannot detect it, so we DISCLOSE it.
    """
    toks = (cmd or "").split()
    if not toks:
        return None
    first = os.path.basename(toks[0]).lower()
    if first in _RUNNER_FIRST:
        return first
    if first == "npm" and len(toks) >= 2 and toks[1].lower() in ("run", "test"):
        return f"npm {toks[1].lower()}"
    return None


_TEST_DIR_SEGMENTS = {"test", "tests", "spec", "specs", "__tests__"}


def _looks_like_test(path):
    """Segment/filename precise — must NOT count `latest.py`, `inspector.py`,
    `contest.ts` as tests (a substring match silently suppressed the advisory)."""
    p = path.replace("\\", "/").lower()
    parts = p.split("/")
    if any(seg in _TEST_DIR_SEGMENTS for seg in parts[:-1]):
        return True
    name = parts[-1]
    stem = name.split(".")[0]
    return (name.startswith("test_") or stem.endswith("_test") or stem.endswith("_spec")
            or ".test." in name or ".spec." in name)


def _has_shell_masking(cmd):
    """True unless the command is a SIMPLE command, optionally `&&`-chained.

    ALLOW-LIST by design: anything that can decouple the shell's exit status from
    the test's status makes the code untrustworthy, and an unrecognised construct
    is treated as untrusted rather than assumed safe. Masking forms include a pipe
    (`a | b` -> b's status), `;`/`&` sequencing, `||` (runs b when a fails), a
    newline (same as `;`), and subshells/backticks.

    `&&` is the one safe chain: it short-circuits, so a failure propagates.
    `2>&1` is a redirect, not a separator, and stays trusted.

    Quoting is platform-aware: cmd.exe does NOT treat `'` as a quote (a naive
    POSIX scanner walks straight past a real `'a|b'` pipeline on Windows), and
    POSIX backslash escapes are honoured.
    """
    s = cmd or ""
    posix = os.name != "nt"
    in_s = in_d = False
    i = 0
    while i < len(s):
        ch = s[i]
        if posix and ch == "\\" and i + 1 < len(s):
            i += 2                      # escaped char is never a delimiter
            continue
        if ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "'" and posix and not in_d:
            in_s = not in_s
        elif not in_s and not in_d:
            if ch == "&":
                if i + 1 < len(s) and s[i + 1] == "&":
                    i += 2              # `&&` — safe, failure propagates
                    continue
                if i > 0 and s[i - 1] == ">":
                    i += 1              # `2>&1` — a redirect, not a separator
                    continue
                return True             # bare `&` sequences/backgrounds
            if ch in ("|", ";", "\n", "\r", "`"):
                return True
            if ch == "$" and i + 1 < len(s) and s[i + 1] == "(":
                return True             # command substitution
        i += 1
    return False


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
    """Run the caller's test command in the worktree, reporting not just pass/fail
    but whether the result can be TRUSTED (exit code meaningful, deps present)."""
    if not test_cmd:
        return None
    trusted = not _has_shell_masking(test_cmd)
    trust_reason = None if trusted else (
        "the command is not a simple or '&&'-chained command (it contains a pipe, ';', "
        "'&', '||', a newline, or a subshell), so the shell's exit code may not be the tests'")
    runner = _delegates_to_runner(test_cmd)
    runner_note = None if not runner else (
        f"test command delegates to '{runner}' — the gate can only judge the top-level "
        "command's shape, not what that script does; make sure it does not mask failures "
        "(e.g. an internal pipe)")
    env_warning = None
    try:
        if (os.path.isfile(os.path.join(worktree, "package.json"))
                and not os.path.isdir(os.path.join(worktree, "node_modules"))):
            env_warning = ("worktree has package.json but no node_modules — JS/TS tests cannot "
                           "resolve dependencies here, so the result is not meaningful")
    except OSError:
        pass
    try:
        p = subprocess.run(test_cmd, cwd=worktree, shell=True, capture_output=True,
                           text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"ran": True, "pass": False, "output_tail": "test run timed out",
                "exit_code_trusted": trusted, "trust_reason": trust_reason,
                "runner_note": runner_note, "env_warning": env_warning}
    except Exception as e:  # noqa: BLE001
        return {"ran": False, "error": str(e)}
    return {"ran": True, "pass": p.returncode == 0,
            "output_tail": ((p.stdout or "") + (p.stderr or ""))[-800:],
            "exit_code_trusted": trusted, "trust_reason": trust_reason,
            "runner_note": runner_note, "env_warning": env_warning}


def assess_gate(files, test_result):
    """APPLICABILITY-FIRST gate. Decide 'does the test gate apply?' BEFORE pass/fail.
    N/A is a first-class clean pass, distinct from a FAIL. `clears` means the
    deterministic gate is satisfied — Claude's diff review is still required."""
    if not files:
        return {"applies": False, "verdict": "empty", "clears": False,
                "reason": "no changes produced", "advisories": []}
    code_changed = any(_is_code_file(f) for f in files)
    advisories = []
    if code_changed and not any(_looks_like_test(f) for f in files):
        advisories.append("new/changed code but no test file in the diff — "
                          "check coverage before merging")
    if isinstance(test_result, dict) and test_result.get("runner_note"):
        advisories.append(test_result["runner_note"])
    if not code_changed:
        return {"applies": False, "verdict": "n/a", "clears": True,
                "reason": "docs/config-only change — test gate does not apply",
                "advisories": advisories}
    if test_result is None or not test_result.get("ran"):
        return {"applies": True, "verdict": "blocked", "clears": False,
                "reason": "code changed but tests were not run", "advisories": advisories}
    # A result we cannot TRUST must never read as green (fail-safe direction).
    # Default FALSE: a result that does not assert its own trust is not trusted.
    if not test_result.get("exit_code_trusted", False):
        return {"applies": True, "verdict": "unverifiable", "clears": False,
                "reason": ((test_result.get("trust_reason")
                            or "the test result did not assert a trustworthy exit code")
                           + " — refusing to report green"),
                "advisories": advisories}
    if test_result.get("env_warning"):
        return {"applies": True, "verdict": "unverifiable", "clears": False,
                "reason": test_result["env_warning"], "advisories": advisories}
    if test_result.get("pass"):
        return {"applies": True, "verdict": "green", "clears": True,
                "reason": "code changed; tests pass", "advisories": advisories}
    return {"applies": True, "verdict": "red", "clears": False,
            "reason": "code changed; tests fail", "advisories": advisories}


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
