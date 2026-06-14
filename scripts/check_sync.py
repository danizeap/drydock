#!/usr/bin/env python3
"""Fail if the two copies of sdd.py have drifted.

The plugin ships sdd.py twice: scripts/sdd.py (authoritative, used in this repo)
and assets/project-scaffold/scripts/sdd.py (the copy distributed to new projects
via /drydock:init-project). They must stay byte-identical — drift here has
silently shipped broken behavior to fresh installs before. Run this before
releasing, or wire it into CI.

Exit 0 if identical, 1 if drifted, 2 if a file is missing.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORITATIVE = REPO_ROOT / "scripts" / "sdd.py"
SCAFFOLD = REPO_ROOT / "assets" / "project-scaffold" / "scripts" / "sdd.py"


def main() -> int:
    for label, path in [("authoritative", AUTHORITATIVE), ("scaffold", SCAFFOLD)]:
        if not path.is_file():
            print(f"error: {label} copy not found: {path}", file=sys.stderr)
            return 2

    a = AUTHORITATIVE.read_bytes()
    b = SCAFFOLD.read_bytes()

    if a == b:
        print("OK: scripts/sdd.py and assets/project-scaffold/scripts/sdd.py are identical.")
        return 0

    print("DRIFT: the two sdd.py copies differ.", file=sys.stderr)
    print(f"  authoritative: {AUTHORITATIVE} ({len(a)} bytes)", file=sys.stderr)
    print(f"  scaffold:      {SCAFFOLD} ({len(b)} bytes)", file=sys.stderr)
    print("Re-sync: copy scripts/sdd.py over the scaffold copy, then re-run.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
