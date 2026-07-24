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
import re
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # scripts/ -> `conductor` importable
from conductor import codex_bridge as cb  # noqa: E402
from conductor import review as rv  # noqa: E402  (secret scan + fence, shared)

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


def _int_or_none(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _num_or_none(v):
    """`isinstance(True, (int, float))` is True in Python, and JSON `true` decodes
    to it — so an unguarded gauge reading turns a boolean into an arithmetic
    result. Guarding the token path and not this one produced a literal `0`."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def summarize_cost(usage, gauge_before, gauge_after, elapsed_s=None):
    """What the run actually cost. Codex's token counts are informative; the fuel
    delta is AUTHORITATIVE — it is what the account was charged.

    Every field is `None` when it could not be measured. A cost report that
    invents a number is worse than one that admits it does not know: the Owner
    would budget against a fiction, and the shortfall arrives silently.
    """
    u = usage if isinstance(usage, dict) else {}
    # Codex has shipped both `input_tokens` and `prompt_tokens` spellings.
    inp = _int_or_none(u.get("input_tokens", u.get("prompt_tokens")))
    out = _int_or_none(u.get("output_tokens", u.get("completion_tokens")))
    cached = _int_or_none(u.get("cached_input_tokens", u.get("cache_read_input_tokens")))
    total = _int_or_none(u.get("total_tokens"))
    # Only a COMPLETE pair yields a total: `(inp or 0) + (out or 0)` silently
    # asserts that the missing half was zero, in a dict whose own note says
    # null means not measured.
    if total is None and inp is not None and out is not None:
        total = inp + out

    def _used(g):
        return _num_or_none(g.get("used_percent")) if isinstance(g, dict) else None

    b, a = _used(gauge_before), _used(gauge_after)
    # Only a real before AND a real after yield a delta; a reset mid-run makes the
    # difference negative and meaningless, so it is reported as unmeasured.
    delta = None
    if isinstance(b, (int, float)) and isinstance(a, (int, float)):
        d = round(a - b, 2)
        delta = d if d >= 0 else None
    return {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out,
            "total_tokens": total, "fuel_used_percent": delta,
            "fuel_before_percent": b, "fuel_after_percent": a,
            "elapsed_s": elapsed_s,
            "note": ("fuel_used_percent is the authoritative cost; token counts are "
                     "Codex-reported. null means not measured, never zero.")}


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


MAX_INLINE_BYTES = 128 * 1024
MAX_INLINE_FILE_BYTES = 64 * 1024
MAX_INLINE_FILES = 64          # names are payload too: 50k names built an 839KB prompt


def build_scoped_task(task, worktree, files):
    """Inline the named edit targets into the task prompt.

    SOFT scoping by design. The reporter's own 3-file change was a tool body, a
    test's expected-tools list, and i18n labels — coupled files that are NOT
    discoverable from the target's name. The files an operator forgets to name are
    exactly the ones that make the change complete, so a hard boundary would turn
    an under-scoped run into a red gate caused by the scoping, not the code.
    Inlining removes the need to CRAWL for the targets; it does not forbid reading.

    Returns (prompt, error). Content leaves the machine here, so the same
    by-name/by-content refusal `review.py` applies to explicitly named paths
    applies here too.
    """
    if not files:
        return task, None
    if len(files) > MAX_INLINE_FILES:
        return None, (f"{len(files)} files named; the limit is {MAX_INLINE_FILES}. Names are "
                      "payload too — scoping is for a small coupled change, so omit --files "
                      "for a wide sweep")
    root = os.path.realpath(worktree)
    blocks, names, total = [], [], 0
    for rel in files:
        rel = rel.replace("\\", "/")
        if os.path.isabs(rel) or (len(rel) > 1 and rel[1] == ":"):
            return None, f"--files takes repo-relative paths; got an absolute path: {rel}"
        full = os.path.normpath(os.path.join(root, *rel.split("/")))
        rp = os.path.realpath(full)
        # CONTAINMENT — `../../../secrets.txt` read straight out of the worktree.
        if not (rp == root or rp.startswith(root + os.sep)):
            return None, f"path resolves outside the worktree: {rel}"
        # realpath in the guard too: without it a hardlink or symlink alias with an
        # innocent name walks a secret file straight past the name check.
        if cb.guard_outbound([rel, full, rp]):
            return None, f"refusing to inline secret-bearing path: {rel}"
        if not os.path.isfile(full):
            # A named target may legitimately not exist yet (a file to be created).
            names.append(rel)
            continue
        # Size AND content from one handle, hard-capped — the same treatment
        # review.py gives an explicitly named path, which R3 promises.
        try:
            with open(full, "rb") as fh:
                size = os.fstat(fh.fileno()).st_size
                if size > MAX_INLINE_FILE_BYTES:
                    return None, (f"{rel} is {size} bytes (> {MAX_INLINE_FILE_BYTES} per-file "
                                  "inline limit)")
                if total + size > MAX_INLINE_BYTES:
                    return None, (f"named files exceed the {MAX_INLINE_BYTES}-byte inline "
                                  "budget — name fewer files, or omit --files")
                raw = fh.read(MAX_INLINE_FILE_BYTES + 1)
        except OSError as e:
            return None, f"{rel}: {e}"
        if len(raw) > MAX_INLINE_FILE_BYTES:
            return None, f"{rel} grew past the {MAX_INLINE_FILE_BYTES} limit while being read"
        text = raw.decode("utf-8", errors="replace")
        if rv.content_has_secret(text):
            return None, f"{rel} contains what looks like secret material; not sending"
        total += len(raw)
        names.append(rel)
        blocks.append((rel, text))

    marker = rv._fence("\n".join(t for _, t in blocks), "\n".join(names), task)
    parts = [task, "\n\n--- EDIT TARGETS ---\n",
             "Start from these files; their current content is included below so you do "
             "not need to search for them. You MAY read or edit other files when the "
             "change genuinely requires it (a test that asserts a list, a translation "
             "file, a caller that must be updated) — anything you touch outside this set "
             "is reported to the reviewer, not blocked. Do not crawl the repository "
             "looking for work that was not asked for.\n",
             "Files in scope: " + ", ".join(names) + "\n"]
    for rel, text in blocks:
        parts.append(f"\n=== BEGIN {marker} {rel} ===\n{text}\n=== END {marker} ===\n")
    return "".join(parts), None


def assess_scope(declared, changed):
    """Which edits landed outside what the operator declared. Disclosure, not a gate."""
    if not declared:
        return None
    def _norm(d):
        d = d.replace("\\", "/")
        # `lstrip("./")` strips a CHARACTER SET, so `.github/…` became `github/…`
        # and every dotfile reported a false out-of-scope edit.
        return d[2:] if d.startswith("./") else d

    norm = {_norm(d) for d in declared}
    touched = [c.replace("\\", "/") for c in changed]
    outside = sorted(c for c in touched if c not in norm)
    untouched = sorted(n for n in norm if n not in set(touched))
    return {"declared": sorted(norm), "out_of_scope": outside,
            "declared_untouched": untouched, "honored": not outside}


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


# PROVISIONAL, and advisory-only until calibrated against real diffs. They decide
# whether a sentence is printed — never whether the gate clears.
WIDE_DIFF_FILES = 8
LOW_REPETITION = 0.45
MAX_SHAPE_FILES = 200          # pairwise comparison is quadratic; bound and disclose it
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUM = re.compile(r"\d+")


def _shape_of(line):
    """Structural signature: identifiers and numbers erased, punctuation kept.

    `add_tool(name, timeout=5)` and `add_tool(other, timeout=9)` collapse to the
    same shape. That is the point — a mechanical sweep adds the same STRUCTURE
    with different names, so comparing raw text would score it as divergent.
    """
    return _NUM.sub("0", _IDENT.sub("#", line)).strip()


_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def _added_shapes(diff):
    """{file: set(shapes)} for added lines, from a unified diff.

    HUNK-AWARE, and it has to be: an added source line whose text is `++ b/x.py`
    renders as `+++ b/x.py`, and a header-by-prefix parser reads it as a file
    boundary. Codex writes the diff, so a naive parser lets the reviewed party
    collapse every file into one phantom key and SUPPRESS its own advisory.
    Inside a hunk, line counts from the `@@` header decide where the body ends —
    content can never be mistaken for structure.
    """
    per, cur = {}, None
    old_left = new_left = 0
    for ln in (diff or "").splitlines():
        if old_left > 0 or new_left > 0:          # inside a hunk body: content only
            c = ln[:1]
            if c == "+":
                new_left -= 1
                if cur:
                    s = _shape_of(ln[1:])
                    if s:
                        per.setdefault(cur, set()).add(s)
            elif c == "-":
                old_left -= 1
            elif c == "\\":                        # "\ No newline at end of file"
                pass
            else:                                  # context line
                old_left -= 1
                new_left -= 1
            old_left, new_left = max(0, old_left), max(0, new_left)
            continue
        m = _HUNK.match(ln)
        if m:
            old_left = int(m.group(1) if m.group(1) is not None else 1)
            new_left = int(m.group(2) if m.group(2) is not None else 1)
        elif ln.startswith("+++ b/"):
            cur = ln[6:].strip()
    return {f: s for f, s in per.items() if s}


def describe_diff_shape(files, diff):
    """Width x cross-file repetition — the reporter's 'awkward middle', measured.

    A wide, REPETITIVE diff is a mechanical sweep and a passing suite means what it
    usually means. A wide, DIVERGENT diff is a dozen separate judgment calls, where
    'tests pass' is the weakest evidence and the human review is doing all the work.
    Nothing here gates; it tells the reviewer when the cheap signal is cheap.
    """
    n = len(files or [])
    per = _added_shapes(diff)
    rep, sampled = None, False
    sets = list(per.values())
    if len(sets) > MAX_SHAPE_FILES:               # bounded, and SAID so — never silent
        sets, sampled = sets[:MAX_SHAPE_FILES], True
    if len(sets) >= 2:
        scores = []
        for i, a in enumerate(sets):
            best = 0.0
            for j, b in enumerate(sets):
                if i == j:
                    continue
                union = len(a | b)
                if union:
                    best = max(best, len(a & b) / union)   # Jaccard on shapes
                if best >= 1.0:
                    break                                  # cannot improve
            scores.append(best)
        rep = round(sum(scores) / len(scores), 3)
    if rep is None:
        # Deletion-only, binary, or unparseable: repetition was NOT measured.
        # Calling that "wide-repetitive" would assert the reassuring case from
        # an absence of evidence — the same fabrication R1 forbids for cost.
        kind = "unknown" if n >= WIDE_DIFF_FILES else "narrow"
    elif n < WIDE_DIFF_FILES:
        kind = "narrow"
    elif rep < LOW_REPETITION:
        kind = "wide-divergent"
    else:
        kind = "wide-repetitive"
    return {"files": n, "repetition": rep, "kind": kind, "sampled": sampled,
            "compared_files": len(sets),
            "thresholds": {"wide_files": WIDE_DIFF_FILES, "low_repetition": LOW_REPETITION}}


def assess_gate(files, test_result, diff_shape=None, scope=None):
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
    if isinstance(diff_shape, dict) and diff_shape.get("kind") == "unknown":
        advisories.append(
            f"{diff_shape['files']} files changed but cross-file repetition could not be "
            "measured (no readable added lines — deletions, binary, or an unparseable "
            "diff), so the shape signal is unavailable here rather than reassuring")
    if isinstance(diff_shape, dict) and diff_shape.get("kind") == "wide-divergent":
        advisories.append(
            f"{diff_shape['files']} files changed with little repetition between them "
            f"(shape similarity {diff_shape['repetition']}) — this is not a mechanical "
            "sweep but a set of separate judgment calls, so a passing test suite is weak "
            "evidence here. Read this diff properly, or split the task.")
    if isinstance(scope, dict) and scope.get("out_of_scope"):
        advisories.append(
            "edited outside the declared --files scope: "
            + ", ".join(scope["out_of_scope"][:8])
            + (" …" if len(scope["out_of_scope"]) > 8 else "")
            + " — often correct (a coupled test or translation file), but review these first")
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


def mutate(task, base="HEAD", test_cmd=None, weight="heavy", model=None, keep=True,
           files=None):
    core = cb.discover_core()
    if not core:
        return {"ok": False, "stage": "discover"}
    gauge = cb.summarize_gauge(cb.read_rate_limits(core))
    model = model or cb.route(weight, gauge)["model"]
    wt, branch, err = create_worktree(base, task)
    if not wt:
        return {"ok": False, "stage": "worktree", "error": err, "gauge": gauge}
    try:
        prompt, scope_err = build_scoped_task(task, wt, files)
        if scope_err:
            cleanup_worktree(wt, branch)
            return {"ok": False, "stage": "scope_guard", "error": scope_err, "gauge": gauge}
        t0 = time.monotonic()
        d = delegate_mutation(core, wt, prompt, model)
        elapsed = round(time.monotonic() - t0, 1)
        # Re-read AFTER the run: the delta is what the account was actually charged.
        gauge_after = cb.summarize_gauge(cb.read_rate_limits(core))
        cost = summarize_cost(d.get("usage"), gauge, gauge_after, elapsed)
        changed, diff = extract_changes(wt, base)
        scope = assess_scope(files, changed)
        shape = describe_diff_shape(changed, diff)
        tests = run_tests(wt, test_cmd)
        gate = assess_gate(changed, tests, shape, scope)
        result = {"ok": True, "gauge": gauge, "gauge_after": gauge_after, "cost": cost,
                  "model": model, "worktree": wt, "branch": branch, "base": base,
                  "delegation": d, "files": changed, "diff": diff,
                  "scope": scope, "diff_shape": shape,
                  "tests": tests, "gate": gate, "clears_gate": gate["clears"],
                  "merged": False,
                  "note": ("NOT merged. Review the diff, then merge deliberately. "
                           "Clearing the gate is necessary, not sufficient — Claude "
                           "must review scope/security/architecture before merge.")}
        if not keep or not changed or not d.get("ok"):
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
    ap.add_argument("--files", nargs="+", metavar="PATH", default=None,
                    help="repo-relative edit targets to inline (opt-in, SOFT scope): Codex "
                         "starts here instead of crawling, may still edit elsewhere, and "
                         "any out-of-scope edit is reported. Best for a small coupled "
                         "change; omit it for a wide mechanical sweep.")
    ap.add_argument("--cleanup", nargs=2, metavar=("WORKTREE", "BRANCH"),
                    help="remove a worktree+branch from a prior run, then exit")
    args = ap.parse_args()
    if args.cleanup:
        cleanup_worktree(args.cleanup[0], args.cleanup[1])
        print(json.dumps({"ok": True, "cleaned_up": args.cleanup}))
        return 0
    if not args.task:
        ap.error("task is required unless --cleanup is used")
    out = mutate(args.task, args.base, args.test_cmd, args.weight, args.model,
                 files=args.files)
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
