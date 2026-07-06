#!/usr/bin/env python3
"""SDD+ change packet helper. Cross-platform replacement for scripts/sdd.ps1.

Commands:
  init                       Create the sdd-plus directory structure.
  new <kebab-change-name>    Create a change packet from templates.
  status                     List active changes and task counts.
  verify <kebab-change-name> Check required artifacts exist and are filled in.
  archive <kebab-change-name> [--force]  Move a completed change to the archive.
"""

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

REQUIRED_FILES = ["brief.md", "plan.md", "tasks.md", "decision-log.md", "verification.md"]
SDD_DIRS = ["sdd-plus", "sdd-plus/standards", "sdd-plus/specs",
            "sdd-plus/specs/capabilities", "sdd-plus/changes",
            "sdd-plus/archive", "sdd-plus/templates"]
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def find_root(require: bool = True) -> Path:
    """Walk up from cwd looking for an sdd-plus directory. Never falls back silently."""
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "sdd-plus").is_dir():
            return candidate
    if require:
        sys.exit("error: no sdd-plus directory found in this or any parent directory. "
                 "Run 'python3 scripts/sdd.py init' (on Windows: 'python') from the project root first.")
    return current


def assert_kebab(name: str) -> None:
    if not name:
        sys.exit("error: change name is required.")
    if not KEBAB.match(name):
        sys.exit("error: change name must be kebab-case, e.g. improve-search-flow.")


def cmd_init() -> None:
    root = find_root(require=False)
    for d in SDD_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
    print(f"Initialized SDD+ directories under {root}")


def render_template(template: Path, target: Path, change_name: str) -> None:
    content = template.read_text(encoding="utf-8-sig")  # tolerate legacy BOMs on read
    content = content.replace("{{CHANGE_NAME}}", change_name)
    content = content.replace("{{DATE}}", datetime.date.today().isoformat())
    target.write_text(content, encoding="utf-8")  # never write a BOM


def cmd_new(name: str) -> None:
    assert_kebab(name)
    root = find_root()
    change_dir = root / "sdd-plus" / "changes" / name
    if change_dir.exists():
        sys.exit(f"error: change already exists: {change_dir.relative_to(root)}")
    change_dir.mkdir(parents=True)
    template_dir = root / "sdd-plus" / "templates"
    for fname in REQUIRED_FILES:
        template = template_dir / fname
        target = change_dir / fname
        if template.is_file():
            render_template(template, target, name)
        else:
            target.write_text(f"# {fname}\n\nChange: {name}\n", encoding="utf-8")
    specs_dir = change_dir / "specs"
    specs_dir.mkdir()
    delta_template = template_dir / "spec-delta.md"
    if delta_template.is_file():
        render_template(delta_template, specs_dir / "EXAMPLE-capability.md.template", name)
    print(f"Created change: {change_dir.relative_to(root)}")
    print("If this change modifies system behavior, add delta specs under "
          f"{specs_dir.relative_to(root)}/<capability>.md")


def task_counts(tasks_path: Path) -> tuple[int, int]:
    if not tasks_path.is_file():
        return 0, 0
    lines = tasks_path.read_text(encoding="utf-8-sig").splitlines()
    complete = sum(1 for l in lines if re.match(r"^\s*-\s*\[[xX]\]\s+", l))
    pending = sum(1 for l in lines if re.match(r"^\s*-\s*\[\s\]\s+", l))
    return complete, pending


def delta_spec_files(change_dir: Path) -> list[Path]:
    specs_dir = change_dir / "specs"
    if not specs_dir.is_dir():
        return []
    return sorted(p for p in specs_dir.glob("*.md") if not p.name.endswith(".template"))


def delta_capabilities_in_file(delta_file: Path) -> list[str]:
    """The capability declared in a single delta file, if it is a valid kebab-case
    name appearing outside any fenced code block. Returns [] when the line is
    missing, still the placeholder, fenced, or not kebab-case — callers fail
    closed on [] rather than skip the sync gate silently."""
    in_code = False
    for line in delta_file.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.lower().startswith("capability:"):
            raw = line.split(":", 1)[1].strip()
            if "<" in raw or ">" in raw:  # unfilled angle-bracket placeholder
                return []
            cap = raw.strip("`").strip()
            if KEBAB.match(cap):
                return [cap]
            return []
    return []


def delta_capabilities(change_dir: Path) -> list[str]:
    caps: list[str] = []
    for f in delta_spec_files(change_dir):
        for cap in delta_capabilities_in_file(f):
            if cap not in caps:
                caps.append(cap)
    return caps


def delta_added_requirements(delta_file: Path) -> list[str]:
    """Requirement names the delta ADDS, per the spec-delta template grammar:
    `### Requirement: <name>` headings appearing under a `## ADDED Requirements`
    section. Used to confirm the living spec actually contains them — i.e. the
    delta was synced, not just that the capability file exists. MODIFIED/REMOVED/
    RENAMED are intentionally not checked here (rarer, harder; see decision-log)."""
    reqs = []
    in_added = False
    in_code = False
    for line in delta_file.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^##(?!#)\s", line):  # any level-2 heading closes the ADDED section
            in_added = bool(re.match(r"^##\s+ADDED\s+Requirements\s*$", line, re.IGNORECASE))
            continue
        if in_added:
            m_req = re.match(r"^###\s+Requirement:\s*(.+?)\s*$", line, re.IGNORECASE)
            if m_req:
                name = m_req.group(1).strip().strip("`")
                if name and not name.startswith("<"):
                    reqs.append(name)
    return reqs


def requirement_present(living_spec: Path, requirement: str) -> bool:
    """True if the living spec has a `### Requirement: <name>` heading whose name
    equals this requirement (whitespace/case-normalized). Exact name, not a
    substring — so 'Session' does not match '### Requirement: Session Expiry'."""
    if not living_spec.is_file():
        return False
    target = " ".join(requirement.strip().strip("`").lower().split())
    in_code = False
    for line in living_spec.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^#{2,4}\s+Requirement:\s*(.+?)\s*$", line, re.IGNORECASE)
        if m:
            name = " ".join(m.group(1).strip().strip("`").lower().split())
            if name == target:
                return True
    return False


def text_has_placeholder(text: str) -> bool:
    """True if the text still carries template placeholder residue. Fenced blocks
    and inline `code` spans are ignored, so a brief/decision-log that quotes a
    placeholder form as an example is not flagged. Detects {{CHANGE_NAME}}, or TBD
    as a whole line / list item / checkbox / real (non-quoted) table cell."""
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        bare = re.sub(r"`[^`]*`", "", line)  # drop inline code spans (mentions)
        if "{{CHANGE_NAME}}" in bare:
            return True
        if re.match(r"^\s*-?\s*(\[[ xX]?\]\s*)?TBD\s*$", bare):
            return True
        if bare.lstrip().startswith("|") and re.search(r"\|\s*TBD\s*\|", bare):
            return True
    return False


def verification_result_is_pending(text: str) -> bool:
    """True if verification.md's `## Result` section is empty or still 'Pending.'."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^##\s+Result\s*$", line, re.IGNORECASE):
            collected = []
            for nxt in lines[i + 1:]:
                if re.match(r"^#{1,6}\s", nxt):
                    break
                if nxt.strip():
                    collected.append(nxt.strip())
            joined = " ".join(collected).strip().lower().rstrip(".")
            return joined in ("", "pending")
    return False


def cmd_status() -> None:
    root = find_root()
    changes_root = root / "sdd-plus" / "changes"
    changes = sorted(p for p in changes_root.iterdir() if p.is_dir()) if changes_root.is_dir() else []
    if not changes:
        print("No active SDD+ changes.")
        return
    for change in changes:
        complete, pending = task_counts(change / "tasks.md")
        deltas = delta_spec_files(change)
        suffix = f", {len(deltas)} delta spec(s)" if deltas else ""
        print(f"{change.name}: {complete} complete, {pending} pending{suffix}")


def cmd_verify(name: str) -> int:
    assert_kebab(name)
    root = find_root()
    change_dir = root / "sdd-plus" / "changes" / name
    if not change_dir.is_dir():
        sys.exit(f"error: change not found: sdd-plus/changes/{name}")

    standards_dir = root / "sdd-plus" / "standards"
    if not standards_dir.is_dir() or not any(standards_dir.iterdir()):
        sys.exit("error: no standards found under sdd-plus/standards.")

    missing = [f for f in REQUIRED_FILES if not (change_dir / f).is_file()]
    if missing:
        sys.exit(f"error: missing required artifacts: {', '.join(missing)}")

    unfilled = []
    for fname in REQUIRED_FILES:
        text = (change_dir / fname).read_text(encoding="utf-8-sig")
        if text_has_placeholder(text) or (
            fname == "verification.md" and verification_result_is_pending(text)
        ):
            unfilled.append(fname)

    complete, pending = task_counts(change_dir / "tasks.md")
    print(f"Verified artifacts for {name}.")
    print(f"Tasks: {complete} complete, {pending} pending.")
    if unfilled:
        print(f"warning: unfilled placeholder content (TBD) remains in: {', '.join(unfilled)}")
    if pending > 0:
        print("Pending tasks remain. Archive will require --force.")
    return 1 if unfilled else 0


def record_override(change_dir: Path, waived: list, reason: str) -> None:
    """Append an auditable override record to the change's decision-log.md.

    Overrides travel with the packet into archive/, so a forced archive always
    leaves a paper trail of which gate(s) were waived and why."""
    entry = (f"\n## Override — {datetime.date.today().isoformat()}\n"
             f"- Gates waived: {'; '.join(waived)}\n"
             f"- Reason: {reason}\n")
    with (change_dir / "decision-log.md").open("a", encoding="utf-8") as f:
        f.write(entry)


def cmd_archive(name: str, force: bool, reason: str = "") -> None:
    if force and not reason:
        sys.exit('error: --force requires --reason "<why>" so the override is auditable '
                 "(it is recorded to the packet's decision-log.md). "
                 f'e.g. archive {name} --force --reason "hotfix; tests tracked in #123".')
    rc = cmd_verify(name)
    root = find_root()
    change_dir = root / "sdd-plus" / "changes" / name
    caps_dir = root / "sdd-plus" / "specs" / "capabilities"
    waived = []
    unattributable = [f.name for f in delta_spec_files(change_dir)
                      if not delta_capabilities_in_file(f)]
    if unattributable:
        if not force:
            sys.exit(
                "error: delta spec(s) with no valid 'Capability:' line: "
                + ", ".join(unattributable)
                + ". Add a kebab-case Capability line, or rerun with --force."
            )
        waived.append("unattributable delta specs (" + ", ".join(unattributable) + ")")
    unsynced = [
        cap for cap in delta_capabilities(change_dir)
        if not (caps_dir / f"{cap}.md").is_file()
    ]
    if unsynced:
        if not force:
            sys.exit(
                "error: delta specs reference capabilities with no living spec yet: "
                + ", ".join(unsynced)
                + ". Run the spec-sync skill (/drydock:sync) first, or rerun with --force."
            )
        waived.append("unsynced capabilities (" + ", ".join(unsynced) + ")")
    missing_reqs = []
    for delta_file in delta_spec_files(change_dir):
        file_caps = delta_capabilities_in_file(delta_file)
        for cap in file_caps:
            living = caps_dir / f"{cap}.md"
            for req in delta_added_requirements(delta_file):
                if not requirement_present(living, req):
                    missing_reqs.append(f"{cap}: {req}")
    if missing_reqs:
        if not force:
            sys.exit(
                "error: these delta requirements are not present in the living spec "
                "(delta not synced?):\n  - "
                + "\n  - ".join(missing_reqs)
                + "\nRun /drydock:sync first, or rerun with --force."
            )
        waived.append("unsynced requirements (" + ", ".join(missing_reqs) + ")")
    _, pending = task_counts(change_dir / "tasks.md")
    if pending > 0 or rc != 0:
        if not force:
            sys.exit("error: cannot archive with pending tasks or unfilled placeholders. "
                     "Complete the packet or rerun with --force.")
        waived.append("pending tasks / unfilled placeholders")
    if force and waived:
        record_override(change_dir, waived, reason)
        print(f"OVERRIDE recorded in decision-log.md: waived {len(waived)} gate(s) — {reason}")
    archive_root = root / "sdd-plus" / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    target = archive_root / f"{datetime.date.today().isoformat()}-{name}"
    if target.exists():
        sys.exit(f"error: archive already exists: {target.relative_to(root)}")
    shutil.move(str(change_dir), str(target))
    print(f"Archived change: {target.relative_to(root)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDD+ change packet helper.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    p_new = sub.add_parser("new")
    p_new.add_argument("name")
    sub.add_parser("status")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("name")
    p_archive = sub.add_parser("archive")
    p_archive.add_argument("name")
    p_archive.add_argument("--force", action="store_true")
    p_archive.add_argument("--reason", default="",
                           help="required with --force: why the gate is being waived "
                                "(recorded to the packet's decision-log.md)")
    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "new":
        cmd_new(args.name)
    elif args.command == "status":
        cmd_status()
    elif args.command == "verify":
        sys.exit(cmd_verify(args.name))
    elif args.command == "archive":
        cmd_archive(args.name, args.force, args.reason)


if __name__ == "__main__":
    main()
