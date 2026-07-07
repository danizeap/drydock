#!/usr/bin/env python3
"""SessionStart hook: orient the agent to Drydock project state and prove the
guardrails respond to a probe.

Read-only. Silent (emits nothing) outside a Drydock project. ALWAYS exits 0 — it
can only ever ADD context, never block, fail, or materially slow a session.

Design notes (each defends a red-teamed failure mode):
- Self-contained: it deliberately does NOT import scripts/sdd.py — both to avoid
  that module's find_root() -> sys.exit() landmine (SystemExit escapes
  `except Exception`) and to be immune to plugin/project version skew. The small
  read-only helpers here are bounded reimplementations.
- Discovery is BOUNDED (not sdd.py's unbounded upward walk): the closest ancestor
  that has sdd-plus/ AND an AGENTS.md marker, stopping at the git-repo root or
  $HOME, excluding the plugin's own tree and the project-scaffold template — so it
  can never orient on a foreign or template project.
- cwd is treated as UNTRUSTED input; the process cwd is never a fallback.
- The guardrail probe runs the guard scripts under THIS interpreter (sys.executable,
  no shell, no python3||python that could hang on a Windows Store stub). It claims
  only what it verifies: the guard SCRIPT blocks under a probe; a separate static
  hooks.json check covers wiring. "live" requires exit==2 AND the expected block
  message AND a benign control that exits 0 — exit code alone is insufficient.
- Emits only derived signals (enum states, counts, kebab-validated names); never
  file content or absolute paths; output is size-capped.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from _drydock_common import (find_drydock_root, plugin_root_from_env, sanitize_sid,
                             state_path, read_state, write_state, new_state, fingerprint_project)

_GUARD_TIMEOUT_S = 2.0        # per probe; subprocess.run kills the child on timeout
_MAX_PACKETS = 25
_MAX_READ_BYTES = 64 * 1024   # cap bytes read from any project file
_MAX_CTX_BYTES = 2000         # cap the emitted additionalContext
_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# --- bounded read-only project helpers -------------------------------------
def _read_head(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.read(_MAX_READ_BYTES)
    except OSError:
        return ""


def _task_counts(tasks_path):
    text = _read_head(tasks_path)
    complete = len(re.findall(r"(?m)^\s*-\s*\[[xX]\]\s+", text))
    pending = len(re.findall(r"(?m)^\s*-\s*\[\s\]\s+", text))
    return complete, pending


def _verification_pending(verif_path):
    text = _read_head(verif_path)
    m = re.search(r"(?im)^##\s+Result\s*$(.*)", text, re.DOTALL)
    tail = m.group(1) if m else text
    return bool(re.search(r"(?im)^\s*Pending\.\s*$", tail))


def _context_state(root):
    ctx = root / "PROJECT_CONTEXT.md"
    if not ctx.is_file():
        return "missing"
    text = _read_head(ctx)
    tbd = len(re.findall(r"(?mi)^\s*-?\s*TBD\s*$", text))
    if tbd >= 3 or "Copy this file to `PROJECT_CONTEXT.md`" in text:
        return "template"
    return "real"


# --- session-state stamp (channel for the Stop-hook completion gate) -------
def _stamp_session_state(root, data):
    """Best-effort: write/refresh the per-session state file the Stop gate reads.
    MERGE semantics — on resume/compact an existing session's baseline and nudge
    ledger are preserved (auto-compaction must not re-arm the nudge). Only a new
    session (startup/clear, or no valid existing file) gets a fresh baseline.
    Orientation never depends on this succeeding."""
    try:
        sid = sanitize_sid(data.get("session_id"))
        if sid is None:
            return
        path = state_path(sid)
        if path is None:
            return
        existing = read_state(path, sid)
        if existing is not None and data.get("source") not in ("startup", "clear"):
            return  # preserve baseline + nudge ledger
        write_state(path, new_state(sid, fingerprint_project(root)))
    except BaseException:
        return


def scan(root):
    ctx = _context_state(root)
    packets = []
    changes = root / "sdd-plus" / "changes"
    try:
        entries = sorted(p for p in changes.iterdir() if p.is_dir()) if changes.is_dir() else []
    except OSError:
        entries = []
    for p in entries:
        if len(packets) >= _MAX_PACKETS:
            packets.append(("truncated", 0, 0, False, True))
            break
        name = p.name if _KEBAB.match(p.name) else "(unnamed)"
        complete, pending = _task_counts(p / "tasks.md")
        unfilled = _verification_pending(p / "verification.md")
        packets.append((name, complete, pending, unfilled, False))
    return ctx, packets


# --- guardrail liveness probe ----------------------------------------------
_PROBES = [
    ("git-safety", "git_safety.py",
     {"tool_name": "Bash", "tool_input": {"command": "git -C . reset --hard"}},
     {"tool_name": "Bash", "tool_input": {"command": "git status"}},
     b"git-safety guardrail"),
    ("secrets", "protect_secrets.py",
     {"tool_name": "Write", "tool_input": {"file_path": ".env"}},
     {"tool_name": "Write", "tool_input": {"file_path": "notes.txt"}},
     b"secrets guardrail"),
]


def _run_guard(guard_path, payload):
    return subprocess.run(
        [sys.executable, str(guard_path)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True, timeout=_GUARD_TIMEOUT_S,
    )


def probe_guard(hooks_dir, script, block_payload, benign_payload, expect):
    """'live' only if the guard exits 2 with the expected message on the block
    payload AND exits 0 on a benign control. Proves the guard SCRIPT responds
    under this interpreter — not that the wired PreToolUse path fires."""
    guard = hooks_dir / script
    try:
        if not guard.is_file():
            return "degraded (script missing)"
        blocked = _run_guard(guard, block_payload)
        benign = _run_guard(guard, benign_payload)
    except (subprocess.TimeoutExpired, OSError):
        return "unverified (probe timed out)"
    if (blocked.returncode == 2
            and expect in (blocked.stderr or b"")
            and benign.returncode == 0):
        return "live"
    return f"degraded (block rc={blocked.returncode}, benign rc={benign.returncode})"


def wiring_ok(hooks_dir):
    """Static check that hooks.json registers both guards on PreToolUse for the
    right tools — catches a matcher/command misconfiguration the probe cannot."""
    try:
        cfg = json.loads((hooks_dir / "hooks.json").read_text(encoding="utf-8"))
        blob = json.dumps(cfg.get("hooks", {}).get("PreToolUse", []))
    except (OSError, ValueError):
        return False
    return ("git_safety.py" in blob and "protect_secrets.py" in blob
            and "Bash" in blob and ("Write" in blob or "Edit" in blob))


def build_context(root, hooks_dir):
    ctx, packets = scan(root)
    lines = ["[Drydock] This repo is under Drydock/SDD+ governance. Session state:"]
    lines.append("- PROJECT_CONTEXT.md: " + {
        "missing": "MISSING — run the first-run interview before meaningful work.",
        "template": "still the TEMPLATE — fill it before meaningful work.",
        "real": "present.",
    }[ctx])
    active = [p for p in packets if not p[4]]
    if active:
        lines.append(f"- Active change packets: {len(active)}")
        for name, comp, pend, unfilled, trunc in packets:
            if trunc:
                lines.append("  - … (list truncated)")
                continue
            flags = []
            if pend:
                flags.append(f"{pend} task(s) pending")
            if unfilled:
                flags.append("verification not filled")
            lines.append(f"  - {name}: {comp} done" + (" — " + ", ".join(flags) if flags else " — ready to verify/archive"))
    else:
        lines.append("- No active change packets.")
    verdicts = "; ".join(f"{label} {probe_guard(hooks_dir, script, bp, gp, exp)}"
                         for (label, script, bp, gp, exp) in _PROBES)
    wired = "registered" if wiring_ok(hooks_dir) else "NOT REGISTERED in hooks.json"
    lines.append(f"- Guardrails (probe under this interpreter): {verdicts}; wiring: {wired}.")
    out = "\n".join(lines)
    encoded = out.encode("utf-8")
    if len(encoded) > _MAX_CTX_BYTES:
        out = encoded[:_MAX_CTX_BYTES].decode("utf-8", "ignore") + "\n… (truncated)"
    return out


def run():
    """Return the additionalContext string, or '' to emit nothing. Never raises."""
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        return ""
    cwd = data.get("cwd")
    if not isinstance(cwd, str) or not cwd or not os.path.isabs(cwd) or not os.path.isdir(cwd):
        return ""  # untrusted/absent cwd -> no-op (never fall back to the process cwd)
    root = find_drydock_root(Path(cwd), plugin_root_from_env())
    if root is None:
        return ""  # not a Drydock project -> silent
    _stamp_session_state(root, data)  # best-effort channel for the Stop gate
    return build_context(root, Path(__file__).resolve().parent)


def main():
    try:
        ctx = run()
        if ctx:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": ctx}}))
    except BaseException:
        # A SessionStart hook must NEVER fail a session. SystemExit is a
        # BaseException, so catch that too. Emit nothing, exit clean.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
