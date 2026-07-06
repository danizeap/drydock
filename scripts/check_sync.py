#!/usr/bin/env python3
"""Fail if any root file has drifted from its shipped scaffold copy.

Several files live twice: once at the repo root (used to develop and dogfood
Drydock) and once under assets/project-scaffold/ (the copy distributed to new
projects via /drydock:init-project). Each pair MUST stay byte-identical — drift
here has silently shipped broken behavior and stale docs to fresh installs.

Run before releasing, or let CI run it. Exit 0 if every pair matches, 1 if any
pair drifted, 2 if a file is missing.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = REPO_ROOT / "assets" / "project-scaffold"

# (root-relative path) — the scaffold copy is the same relative path under SCAFFOLD.
PAIRS = [
    "scripts/sdd.py",
    "scripts/sdd.ps1",
    "CLAUDE.md",
    "AGENTS.md",
    "sdd-plus/templates/brief.md",
    "sdd-plus/templates/plan.md",
    "sdd-plus/templates/tasks.md",
    "sdd-plus/templates/decision-log.md",
    "sdd-plus/templates/verification.md",
    "sdd-plus/templates/spec-delta.md",
]


def main() -> int:
    drift, missing = [], []
    for rel in PAIRS:
        root_file = REPO_ROOT / rel
        scaffold_file = SCAFFOLD / rel
        if not root_file.is_file():
            missing.append(str(root_file))
            continue
        if not scaffold_file.is_file():
            missing.append(str(scaffold_file))
            continue
        if root_file.read_bytes() != scaffold_file.read_bytes():
            drift.append(rel)

    if missing:
        for m in missing:
            print(f"error: expected file not found: {m}", file=sys.stderr)
        return 2
    if drift:
        print("DRIFT: these root files differ from their scaffold copies:", file=sys.stderr)
        for rel in drift:
            print(f"  - {rel}  (root vs assets/project-scaffold/{rel})", file=sys.stderr)
        print("Re-sync by copying the authoritative root file over the scaffold copy, "
              "then re-run.", file=sys.stderr)
        return 1

    print(f"OK: all {len(PAIRS)} root/scaffold pairs are identical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
