#!/usr/bin/env python3
"""The HANDOFF ritual — the endurance substrate.

When one leader's tank runs low (or the Owner switches drivers), it writes a
fixed-shape HANDOFF.md capturing exactly where things stand, so the incoming
leader (a fresh Claude, a Codex, a future Kimi) resumes from reality instead of
a stale recap. State is gathered deterministically from git + the packet tree +
the executor fleet; the outgoing leader supplies only the one-line next step.

Read-only: gathering never mutates. Writing only touches HANDOFF.md.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # scripts/ -> `conductor` importable
from conductor import executors as ex  # noqa: E402


def _git(args, timeout=30):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        class _R:  # noqa: N801
            returncode, stdout, stderr = 1, "", ""
        return _R()


def _codex_worktrees():
    """Open worktrees on a `codex/` branch — i.e. Codex's unmerged work."""
    out = _git(["worktree", "list", "--porcelain"]).stdout
    trees, cur = [], {}

    def flush():
        if cur.get("branch") and "codex/" in cur["branch"]:
            trees.append(dict(cur))

    for line in out.splitlines():
        if line.startswith("worktree "):
            flush()
            cur = {"path": line[len("worktree "):]}
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch "):]
    flush()
    return trees


def _active_packets():
    base = os.path.join(os.getcwd(), "sdd-plus", "changes")
    if not os.path.isdir(base):
        return []
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(base, "*"))
                  if os.path.isdir(p))


def gather_state():
    """Deterministic snapshot: branch, HEAD, active packets, open codex worktrees, fleet fuel."""
    return {
        "branch": _git(["branch", "--show-current"]).stdout.strip() or "(unknown)",
        "head": _git(["log", "--oneline", "-1"]).stdout.strip() or "(no commits)",
        "active_packets": _active_packets(),
        "codex_worktrees": _codex_worktrees(),
        "fleet": ex.fleet_status(),
    }


def fleet_recommendation(fleet):
    """Advisory routing: which tank to spend, which is low. Full 'spend the
    near-reset tank, protect the far one' logic realizes once >1 tank is usable."""
    tanks = []
    for e in fleet.get("executors", []):
        f = e.get("fuel") or {}
        if e.get("available") and e.get("verified") and f.get("ok"):
            tanks.append((e["name"], f.get("remaining_percent"), f.get("resets_in_hours")))
    notes = ["claude: human-tracked — Owner reports when it's getting low."]
    if not tanks:
        notes.append("No machine-readable executor fuel; running Claude-solo or executors absent.")
    else:
        for name, rem, resets in tanks:
            flag = " ⚠ LOW" if isinstance(rem, int) and rem < 15 else ""
            notes.append(f"{name}: {rem}% left, resets in ~{resets}h{flag}")
        # prefer spending the tank closest to its reset (fuel about to be free)
        with_reset = [t for t in tanks if isinstance(t[2], (int, float))]
        if with_reset:
            spend = min(with_reset, key=lambda t: t[2])
            notes.append(f"→ prefer spending '{spend[0]}' (closest to reset); protect the rest.")
    return notes


def render(state, next_step, notes, stamp):
    fleet = state["fleet"]
    lines = [f"# HANDOFF — {stamp}", ""]
    lines += ["## Where we are",
              f"- Branch: `{state['branch']}`",
              f"- HEAD: {state['head']}",
              f"- Active change packets: {', '.join(state['active_packets']) or '(none)'}"]
    if state["codex_worktrees"]:
        lines.append("- Open Codex worktrees (unmerged work):")
        for w in state["codex_worktrees"]:
            lines.append(f"  - `{w.get('branch')}` at `{w.get('path')}`")
    else:
        lines.append("- Open Codex worktrees: (none)")
    lines += ["", "## Fleet fuel"]
    for rec in fleet_recommendation(fleet):
        lines.append(f"- {rec}")
    lines += ["", "## Next step (the single most important thing)", next_step or "(fill this in)"]
    if notes:
        lines += ["", "## Notes", notes]
    lines.append("")
    return "\n".join(lines)


def write_handoff(next_step, notes="", path="HANDOFF.md", stamp=None):
    stamp = stamp or _now_iso()
    md = render(gather_state(), next_step, notes, stamp)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return path


def read_handoff(path="HANDOFF.md"):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _now_iso():
    # local import so the module is importable in environments that stub time
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def main():
    ap = argparse.ArgumentParser(description="Write or read the HANDOFF.md relay.")
    ap.add_argument("action", choices=["write", "read", "state"], help="write / read HANDOFF.md, or dump state")
    ap.add_argument("--next", dest="next_step", default="", help="the one-line next step (write)")
    ap.add_argument("--notes", default="", help="freeform notes (write)")
    ap.add_argument("--path", default="HANDOFF.md")
    args = ap.parse_args()
    if args.action == "state":
        print(json.dumps(gather_state(), indent=2))
    elif args.action == "read":
        content = read_handoff(args.path)
        print(content if content is not None else json.dumps({"ok": False, "error": "no HANDOFF.md"}))
    else:
        p = write_handoff(args.next_step, args.notes, args.path)
        print(json.dumps({"ok": True, "wrote": p}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
