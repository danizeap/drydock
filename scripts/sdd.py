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


def delta_heading_issues(delta_file: Path) -> list[str]:
    """Non-canonical requirement headings under `## ADDED Requirements`. The living
    specs use `### Requirement: <name>`; a delta authored as `### R5 — <name>` is
    NOT machine-verifiable — `delta_added_requirements` returns [] for it, so the
    'is this delta synced?' gate passes VACUOUSLY and an unsynced delta can archive
    clean. Surfacing these headings is what lets verify warn and the ready-prompt
    refuse to claim READY on grammar it cannot confirm. Returns the offending lines."""
    issues, in_added, in_code = [], False, False
    for line in delta_file.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^##(?!#)\s", line):
            in_added = bool(re.match(r"^##\s+ADDED\s+Requirements\s*$", line, re.IGNORECASE))
            continue
        # a level-3 heading under ADDED that is not the canonical Requirement: form
        if in_added and re.match(r"^###\s", line) and not re.match(
                r"^###\s+Requirement:\s*\S", line, re.IGNORECASE):
            issues.append(line.strip())
    return issues


def packet_unfilled(change_dir: Path) -> list[str]:
    """Required files still carrying template placeholders or a pending Result."""
    unfilled = []
    for fname in REQUIRED_FILES:
        f = change_dir / fname
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8-sig")
        if text_has_placeholder(text) or (
            fname == "verification.md" and verification_result_is_pending(text)
        ):
            unfilled.append(fname)
    return unfilled


def archive_readiness(change_dir: Path, caps_dir: Path) -> list[tuple[str, str]]:
    """The single, pure, read-only list of WAIVABLE blockers between a packet and
    archive. cmd_archive enforces it and the ready-prompt reads it, so the prompt
    can NEVER claim ready when archive would block — they consult one function.
    Returns [(category, message), ...]; an empty list means archive-eligible.

    Deliberately does not fabricate confidence: it reports what is provably wrong.
    Grammar it cannot machine-verify is surfaced separately (delta_heading_issues)
    so the ready-prompt fails toward 'needs sync' rather than a vacuous pass."""
    blockers: list[tuple[str, str]] = []
    unattributable = [f.name for f in delta_spec_files(change_dir)
                      if not delta_capabilities_in_file(f)]
    if unattributable:
        blockers.append(("unattributable",
                         "delta spec(s) with no valid 'Capability:' line: "
                         + ", ".join(unattributable)))
    unsynced = [cap for cap in delta_capabilities(change_dir)
                if not (caps_dir / f"{cap}.md").is_file()]
    if unsynced:
        blockers.append(("unsynced-capability",
                         "capabilities with no living spec yet: " + ", ".join(unsynced)))
    missing_reqs = []
    for delta_file in delta_spec_files(change_dir):
        for cap in delta_capabilities_in_file(delta_file):
            living = caps_dir / f"{cap}.md"
            for req in delta_added_requirements(delta_file):
                if not requirement_present(living, req):
                    missing_reqs.append(f"{cap}: {req}")
    if missing_reqs:
        blockers.append(("missing-requirement",
                         "delta requirements not present in the living spec "
                         "(delta not synced?): " + "; ".join(missing_reqs)))
    unfilled = packet_unfilled(change_dir)
    _, pending = task_counts(change_dir / "tasks.md")
    if unfilled or pending > 0:
        detail = []
        if pending > 0:
            detail.append(f"{pending} pending task(s)")
        if unfilled:
            detail.append("unfilled placeholders in " + ", ".join(unfilled))
        blockers.append(("incomplete", "; ".join(detail)))
    return blockers


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


def _classify_packet(change_dir: Path, caps_dir: Path) -> tuple[str, str]:
    """Bucket one packet. Robust by construction: any error becomes UNKNOWN, so a
    single broken packet (a missing REQUIRED_FILE — precisely the messiest backlog
    entries) never aborts the batch. Uses the same predicates as verify/archive."""
    try:
        missing = [f for f in REQUIRED_FILES if not (change_dir / f).is_file()]
        if missing:
            return "IN-PROGRESS", "missing " + ", ".join(missing)
        _, pending = task_counts(change_dir / "tasks.md")
        if pending > 0:
            return "IN-PROGRESS", f"{pending} pending task(s)"
        unfilled = packet_unfilled(change_dir)
        if unfilled:
            return "CLAIMED-DONE-UNVERIFIED", "tasks done; unfilled: " + ", ".join(unfilled)
        if any(delta_heading_issues(f) for f in delta_spec_files(change_dir)):
            return "NEEDS-SYNC", "non-canonical delta grammar; run /drydock:sync"
        if archive_readiness(change_dir, caps_dir):
            return "NEEDS-SYNC", "delta specs not yet in the living specs"
        return "ARCHIVE-READY", "verified + synced"
    except Exception as e:  # noqa: BLE001 — a triage crash must never abort the sweep
        return "UNKNOWN", str(e)[:70]


_TRIAGE_ORDER = ["ARCHIVE-READY", "NEEDS-SYNC", "CLAIMED-DONE-UNVERIFIED",
                 "IN-PROGRESS", "UNKNOWN"]
_TRIAGE_NEXT = {
    "ARCHIVE-READY": "python3 scripts/sdd.py archive <name>",
    "NEEDS-SYNC": "/drydock:sync <name>, then archive",
    "CLAIMED-DONE-UNVERIFIED": "fill verification.md + /drydock:verify <name>  "
                               "(or archive <name> --abandon --reason \"…\" if truly abandoned)",
    "IN-PROGRESS": "finish the packet, or abandon it",
    "UNKNOWN": "inspect by hand",
}


def cmd_triage() -> None:
    """Read-only. Bucket every active packet and print a per-bucket next action, so
    a backlog can be drained deliberately: archive the ready ones, sync the rest,
    and make an explicit per-packet call on the ones abandoned mid-lifecycle."""
    root = find_root()
    changes = root / "sdd-plus" / "changes"
    caps_dir = root / "sdd-plus" / "specs" / "capabilities"
    dirs = sorted(p for p in changes.iterdir() if p.is_dir()) if changes.is_dir() else []
    dirs = [d for d in dirs if KEBAB.match(d.name)]
    if not dirs:
        print("No active SDD+ changes.")
        return
    buckets: dict[str, list] = {}
    for ch in dirs:
        bucket, detail = _classify_packet(ch, caps_dir)
        buckets.setdefault(bucket, []).append((ch.name, detail))
    print(f"{len(dirs)} active packet(s):")
    for bucket in _TRIAGE_ORDER:
        items = buckets.get(bucket, [])
        if not items:
            continue
        print(f"\n{bucket} ({len(items)}) — next: {_TRIAGE_NEXT[bucket]}")
        for nm, detail in items:
            print(f"  - {nm}: {detail}")


def cmd_verify(name: str, show_ready_prompt: bool = True) -> int:
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

    unfilled = packet_unfilled(change_dir)
    complete, pending = task_counts(change_dir / "tasks.md")
    print(f"Verified artifacts for {name}.")
    print(f"Tasks: {complete} complete, {pending} pending.")
    if unfilled:
        print(f"warning: unfilled placeholder content (TBD) remains in: {', '.join(unfilled)}")
    if pending > 0:
        print("Pending tasks remain. Archive will require --force.")

    # Delta grammar lint — surfaced every verify. Non-canonical headings make the
    # sync gate unverifiable, so they are worth naming even when the packet is green.
    heading_issues = [iss for f in delta_spec_files(change_dir)
                      for iss in delta_heading_issues(f)]
    if heading_issues:
        print(f"warning: {len(heading_issues)} delta requirement heading(s) are not the "
              "canonical '### Requirement: <name>' form (e.g. "
              f"{heading_issues[0]!r}); sync cannot be machine-verified until they are "
              "normalized. Run /drydock:sync.")

    # Ready-to-archive prompt: the well-timed moment green is learned. It FAILS
    # TOWARD 'needs sync' — READY prints only on positive confirmation, never from a
    # merely empty blocker list, so a non-canonical or unsynced delta cannot read as
    # ready. This closes the pre-existing vacuous-pass hole.
    if show_ready_prompt and not unfilled and pending == 0:
        caps_dir = root / "sdd-plus" / "specs" / "capabilities"
        blockers = archive_readiness(change_dir, caps_dir)
        if heading_issues:
            print("Not archive-ready: delta grammar is not machine-verifiable — "
                  "run /drydock:sync, then verify again.")
        elif blockers:
            sync_only = all(c in ("unsynced-capability", "missing-requirement")
                            for c, _ in blockers)
            if sync_only:
                print("Nearly there: delta specs aren't synced into the living specs "
                      "yet. Run /drydock:sync, then archive.")
            else:
                print("Not archive-ready: " + "; ".join(m for _, m in blockers))
        else:
            print(f"READY TO ARCHIVE — run: python scripts/sdd.py archive {name}")
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


def _replace_result_section(text: str, new_body: str) -> str:
    """Replace the `## Result` section with a NORMALIZED `## Result` heading + new_body
    (append one if absent). The heading match is liberal (`## Result:`, `## Result PASS`)
    and the heading line is rewritten clean — so a stray verdict written onto a
    malformed heading line cannot survive an abandon."""
    lines = text.splitlines()
    out, i, replaced = [], 0, False
    while i < len(lines):
        if re.match(r"^##\s+Result\b", lines[i], re.IGNORECASE):
            out.extend(["## Result", "", new_body])   # drop any inline text on the heading
            i += 1
            while i < len(lines) and not re.match(r"^#{1,6}\s", lines[i]):
                i += 1
            replaced = True
            continue
        out.append(lines[i])
        i += 1
    if not replaced:
        out.extend(["", "## Result", "", new_body])
    return "\n".join(out) + "\n"


def _unsynced_requirements(change_dir: Path, caps_dir: Path) -> list[str]:
    """Canonical delta requirements not present in a living spec — the spec
    knowledge an abandon would entomb unharvested (non-canonical grammar cannot be
    checked, so it is not counted as safely-synced either)."""
    missing = []
    for f in delta_spec_files(change_dir):
        for cap in delta_capabilities_in_file(f):
            living = caps_dir / f"{cap}.md"
            for req in delta_added_requirements(f):
                if not requirement_present(living, req):
                    missing.append(f"{cap}: {req}")
    return missing


def cmd_abandon(name: str, reason: str) -> None:
    """Archive a packet as ABANDONED — never verified. Distinct from --force: it
    records the ABSENCE of a verification (never a synthesized PASS), warns when it
    buries unsynced spec knowledge, and — like archive — only MOVES, never deletes."""
    if not reason.strip():
        sys.exit('error: --abandon requires a non-empty --reason "<why>" — the honest '
                 "record of why this packet is being buried unverified.")
    assert_kebab(name)
    root = find_root()
    change_dir = root / "sdd-plus" / "changes" / name
    caps_dir = root / "sdd-plus" / "specs" / "capabilities"
    if not change_dir.is_dir():
        sys.exit(f"error: change not found: sdd-plus/changes/{name}")
    archive_root = root / "sdd-plus" / "archive"
    target = archive_root / f"{datetime.date.today().isoformat()}-{name}"
    # Collision check BEFORE any mutation, so a name clash leaves the packet fully
    # intact in changes/ (never a half-abandoned packet, never a duplicate Override).
    if target.exists():
        sys.exit(f"error: archive already exists: {target.relative_to(root)}")

    # Warn about ALL spec knowledge this abandon buries — canonical unsynced
    # requirements AND deltas whose sync cannot even be verified (non-canonical
    # grammar or no Capability line). triage and verify are loud about these; abandon
    # — the permanently-lossy operation, run on precisely these messy packets — must
    # not be the one place that goes quiet.
    entombed = _unsynced_requirements(change_dir, caps_dir)
    unverifiable = sorted(f.name for f in delta_spec_files(change_dir)
                          if delta_heading_issues(f) or not delta_capabilities_in_file(f))
    if entombed or unverifiable:
        print("warning: this abandon buries spec knowledge not in the living specs "
              "(it will not be harvested):")
        if entombed:
            print("  - unsynced requirements: " + "; ".join(entombed))
        if unverifiable:
            print("  - deltas whose sync cannot be verified (non-canonical grammar or "
                  "no Capability line): " + ", ".join(unverifiable))

    verif = change_dir / "verification.md"
    text = verif.read_text(encoding="utf-8-sig") if verif.is_file() \
        else "# Verification\n\n## Result\n\nPending.\n"
    body = (f"Abandoned {datetime.date.today().isoformat()} — never verified. "
            f"Reason: {reason}")
    verif.write_text(_replace_result_section(text, body), encoding="utf-8")

    waived = ["ABANDONED — never verified (archive gates not checked)"]
    if entombed:
        waived.append("entombs unsynced requirements (" + "; ".join(entombed) + ")")
    if unverifiable:
        waived.append("entombs unverifiable deltas (" + ", ".join(unverifiable) + ")")
    record_override(change_dir, waived, reason)

    archive_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(change_dir), str(target))
    print(f"Abandoned (never verified) and moved to: {target.relative_to(root)}")


def cmd_archive(name: str, force: bool, reason: str = "") -> None:
    if force and not reason:
        sys.exit('error: --force requires --reason "<why>" so the override is auditable '
                 "(it is recorded to the packet's decision-log.md). "
                 f'e.g. archive {name} --force --reason "hotfix; tests tracked in #123".')
    cmd_verify(name, show_ready_prompt=False)  # prints status; hard-exits on missing artifacts
    root = find_root()
    change_dir = root / "sdd-plus" / "changes" / name
    caps_dir = root / "sdd-plus" / "specs" / "capabilities"

    # One shared readiness check — the same list the ready-prompt reads, so the
    # prompt can never disagree with what archive enforces.
    blockers = archive_readiness(change_dir, caps_dir)
    waived = [msg for _, msg in blockers]
    if blockers and not force:
        lines = "\n".join(f"  - {msg}" for _, msg in blockers)
        hint = ("Run /drydock:sync first" if any(
            c in ("unsynced-capability", "missing-requirement") for c, _ in blockers)
            else "Complete the packet")
        sys.exit(f"error: not archive-ready:\n{lines}\n{hint}, or rerun with --force.")
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
    sub.add_parser("triage")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("name")
    p_archive = sub.add_parser("archive")
    p_archive.add_argument("name")
    p_archive.add_argument("--force", action="store_true")
    p_archive.add_argument("--abandon", action="store_true",
                           help="archive as ABANDONED — never verified (distinct from "
                                "--force); records the absence of a result, never a PASS")
    p_archive.add_argument("--reason", default="",
                           help="required with --force or --abandon: why "
                                "(recorded to the packet's decision-log.md)")
    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "new":
        cmd_new(args.name)
    elif args.command == "status":
        cmd_status()
    elif args.command == "triage":
        cmd_triage()
    elif args.command == "verify":
        sys.exit(cmd_verify(args.name))
    elif args.command == "archive":
        if args.abandon:
            if args.force:
                sys.exit("error: use either --abandon or --force, not both — they are "
                         "different dispositions (abandon records 'never verified'; "
                         "force waives a specific gate on work you stand behind).")
            cmd_abandon(args.name, args.reason)
        else:
            cmd_archive(args.name, args.force, args.reason)


if __name__ == "__main__":
    main()
