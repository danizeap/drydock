#!/usr/bin/env python3
"""Drydock release helper: keep the version in lockstep and gate on the tests.

The project version is declared in four hand-editable places, which drift:
  - .claude-plugin/plugin.json         "version": "X"
  - .claude-plugin/marketplace.json    plugins[].version "X"
  - docs/AI_OPERATOR_GUIDE.md           VERSION: Drydock X | ...
  - CHANGELOG.md                        ## X   (heading must already exist)

Usage:
  python scripts/release.py --check        # verify all four agree (CI + preflight); no writes
  python scripts/release.py <version>       # bump all four, run tests + check_sync, print git commands
  python scripts/release.py <version> --dry-run   # show what a bump would do, write nothing

This tool NEVER runs git or any network/history-mutating operation. It prints the
exact commit/tag/push commands for the Owner to run. Dev-only; not shipped in the
project scaffold. Stdlib only, Python 3.9+.

Exit codes: 0 = OK, 1 = drift / preflight failure, 2 = usage / bad version.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _write(rel, text):
    (REPO_ROOT / rel).write_text(text, encoding="utf-8")


# Each location: (label, rel-path, compiled regex with one capturing group around
# the version token). The same regex is used to READ (group 1) and to REWRITE
# (substitute a new token while preserving surrounding text exactly).
LOCATIONS = [
    ("plugin.json", ".claude-plugin/plugin.json",
     re.compile(r'("version"\s*:\s*")(\d+\.\d+\.\d+)(")')),
    ("marketplace.json", ".claude-plugin/marketplace.json",
     re.compile(r'("version"\s*:\s*")(\d+\.\d+\.\d+)(")')),
    ("operator-guide", "docs/AI_OPERATOR_GUIDE.md",
     re.compile(r'(VERSION:\s*Drydock\s+)(\d+\.\d+\.\d+)(\s*\|)')),
]

CHANGELOG = "CHANGELOG.md"


def read_versions():
    """Return {label: version-or-None} for every declaring location + changelog top."""
    out = {}
    for label, rel, rx in LOCATIONS:
        m = rx.search(_read(rel))
        out[label] = m.group(2) if m else None
    # changelog: the first '## X.Y.Z' heading is the current release
    m = re.search(r"^##\s+(\d+\.\d+\.\d+)", _read(CHANGELOG), re.MULTILINE)
    out["changelog-top"] = m.group(1) if m else None
    return out


def changelog_has(version):
    return re.search(rf"^##\s+{re.escape(version)}\b", _read(CHANGELOG), re.MULTILINE) is not None


def version_tuple(v):
    return tuple(int(p) for p in v.split("."))


def cmd_check():
    versions = read_versions()
    declared = {k: v for k, v in versions.items() if k != "changelog-top"}
    distinct = set(declared.values())
    ok = True
    print("Version locations:")
    for k, v in versions.items():
        print(f"  {k:16} {v}")
    if None in declared.values():
        print("\nERROR: a version location could not be parsed (see None above).", file=sys.stderr)
        ok = False
    elif len(distinct) > 1:
        print(f"\nDRIFT: declaring locations disagree: {sorted(distinct)}", file=sys.stderr)
        ok = False
    # the current declared version should have a changelog entry
    current = next(iter(distinct)) if len(distinct) == 1 else None
    if current and not changelog_has(current):
        print(f"\nERROR: CHANGELOG.md has no '## {current}' entry for the current version.", file=sys.stderr)
        ok = False
    if ok:
        print(f"\nOK: all version locations agree at {current} with a CHANGELOG entry.")
        return 0
    return 1


def cmd_bump(new_version, dry_run):
    if not VERSION_RE.match(new_version):
        print(f"error: '{new_version}' is not a X.Y.Z version.", file=sys.stderr)
        return 2

    versions = read_versions()
    declared = {k: v for k, v in versions.items() if k != "changelog-top"}
    distinct = set(declared.values())
    if len(distinct) != 1 or None in distinct:
        print("error: current version locations are not in sync; run --check and fix first.", file=sys.stderr)
        return 1
    current = next(iter(distinct))
    if version_tuple(new_version) <= version_tuple(current):
        print(f"error: {new_version} is not greater than current {current}.", file=sys.stderr)
        return 2
    if not changelog_has(new_version):
        print(f"error: add a '## {new_version}' section with real notes to CHANGELOG.md first.", file=sys.stderr)
        return 1

    # rewrite each declaring location
    for label, rel, rx in LOCATIONS:
        text = _read(rel)
        new_text, n = rx.subn(lambda m: m.group(1) + new_version + m.group(3), text)
        if n != 1:
            print(f"error: expected exactly one version token in {rel}, found {n}.", file=sys.stderr)
            return 1
        if dry_run:
            print(f"[dry-run] {rel}: {current} -> {new_version}")
        else:
            _write(rel, new_text)
            print(f"bumped {rel}: {current} -> {new_version}")

    if dry_run:
        print("[dry-run] would now run: pytest, check_sync.py")
        return 0

    # preflight: tests + sync guard must pass on the bumped tree
    for label, argv in (("pytest", [sys.executable, "-m", "pytest", "tests/", "-q"]),
                        ("check_sync", [sys.executable, "scripts/check_sync.py"])):
        print(f"\n=== preflight: {label} ===")
        rc = subprocess.run(argv, cwd=REPO_ROOT).returncode
        if rc != 0:
            print(f"error: {label} failed (exit {rc}); release aborted. "
                  f"Version files were bumped — revert with `git checkout -- .` or fix and re-run.",
                  file=sys.stderr)
            return 1

    tag = f"v{new_version}"
    print(f"\nRelease {new_version} is ready. Publish with:\n")
    print(f"  git add -A")
    print(f"  git commit -m \"release: {new_version}\"")
    print(f"  git tag {tag}")
    print(f"  git push origin HEAD --tags")
    print("\n(This tool did not run git. Run the commands above to publish.)")
    return 0


def main(argv):
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    if "--check" in args:
        return cmd_check()
    dry_run = "--dry-run" in args
    positional = [a for a in args if not a.startswith("--")]
    if len(positional) != 1:
        print("usage: release.py --check | release.py <version> [--dry-run]", file=sys.stderr)
        return 2
    return cmd_bump(positional[0], dry_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
