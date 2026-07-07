#!/usr/bin/env python3
"""PreToolUse hook: catch ungoverned work in a Drydock project.

Risk-tiered response to Write/Edit/MultiEdit (and, for the deny tier only, Bash
write targets) when NO change packet is active:

  SILENT — not a Drydock project; target outside the project; an active packet
           exists; or the path is exempt (sdd-plus/, .claude/ config UI files,
           *.md docs, licenses/git metadata). LITE work stays frictionless.
  WARN   — once per session (allow + additionalContext): in-project source edit
           with no packet. Orientation, not enforcement.
  DENY   — narrow, red-team-approved high-risk paths (schema migrations, NEW CI
           workflow files, Dockerfiles/compose) with no packet. Recoverable:
           open a packet and retry.

Fail direction: silent-allow on any error (except the deliberate deny tier).
Always exits 0. Never emits updatedInput (would desync sibling hooks). The
deny reason is a fixed template; classification is lexical on the normalized
path — never dependent on target filesystem state (a NEW file classifies the
same as an existing one), with one deliberate exception: CI-config paths deny
only on CREATION (a new workflow is an exfiltration vector; editing an existing
one is routine and only warns).
"""
import json
import os
import sys
from pathlib import Path

from _drydock_common import (append_event, bash_write_targets, find_drydock_root,
                             plugin_root_from_env, sanitize_sid, state_path, read_state,
                             write_state, new_state, fingerprint_project)

# Path segments that suppress the deny tier: test/fixture/example work in a
# high-risk-named directory is not high-risk work.
_SOFT_SEGMENTS = {"test", "tests", "__tests__", "spec", "specs", "fixtures", "e2e",
                  "stories", "__mocks__", "__snapshots__", "examples", "example",
                  "samples", "docs", "doc"}

# Exempt basenames / extensions (LITE work; checked before everything else).
_EXEMPT_BASENAMES = {"license", "license.txt", "notice", ".gitignore", ".gitattributes",
                     ".editorconfig", "codeowners"}
_EXEMPT_SUFFIXES = (".md", ".markdown", ".rst", ".txt")


def _parts(path_str):
    """Casefolded path segments of a normalized path string."""
    return [p.casefold() for p in Path(path_str.replace("\\", "/")).parts]


def _norm(path_str, cwd):
    """Absolute, normalized, best-effort-resolved form of a target path."""
    if not os.path.isabs(path_str):
        path_str = os.path.join(cwd, path_str)
    p = Path(os.path.normpath(path_str))
    try:
        return p.resolve()  # neutralizes 8.3 short names / symlink laundering
    except OSError:
        return p


def _inside(target, root):
    try:
        target.relative_to(root)
        return True
    except ValueError:
        try:
            return os.path.commonpath([os.path.normcase(str(target)),
                                       os.path.normcase(str(root))]) == os.path.normcase(str(root))
        except ValueError:
            return False


def _rel_parts(target, root):
    """Casefolded segments of target RELATIVE to the project root. Classification
    must never see ancestor directories above the project — a project that lives
    under a folder named 'migrations' is not itself a migration (wrongful-deny
    class found by adversarial verification)."""
    try:
        rel = target.relative_to(root)
    except ValueError:
        rel = target
    return _parts(str(rel))


def is_exempt(target, root):
    """Tier 1: paths where packetless work is always fine. Checked BEFORE deny —
    docs inside a migrations/ dir are docs (deliberate, documented precedence)."""
    rel_parts = _rel_parts(target, root)
    base = target.name.casefold()
    if base in _EXEMPT_BASENAMES or base.endswith(_EXEMPT_SUFFIXES):
        return True
    if "sdd-plus" in rel_parts:
        return True  # the governance files themselves
    if ".claude" in rel_parts and not base.startswith("settings"):
        return True  # agent config lane, except permission-bearing settings*.json
    return False


def _ci_config(parts, base):
    if ".github" in parts and "workflows" in parts:
        return True
    return base in (".gitlab-ci.yml", ".gitlab-ci.yaml", "jenkinsfile")


def is_high_risk(target, root):
    """Narrow deny classes, lexical + casefolded, on the PROJECT-RELATIVE path
    only. Test/fixture/docs segments suppress. Returns a class label or None."""
    parts = _rel_parts(target, root)
    base = target.name.casefold()
    if _SOFT_SEGMENTS.intersection(parts):
        return None
    db_migrate_adjacent = any(parts[i] == "db" and parts[i + 1] == "migrate"
                              for i in range(len(parts) - 1))
    if "migrations" in parts or db_migrate_adjacent:
        return "schema migration"
    if _ci_config(parts, base):
        # creation of a new CI config is the high-risk act; edits are routine
        try:
            exists = target.exists()
        except OSError:
            exists = True  # on doubt, treat as existing -> warn tier, never wrong-deny
        return None if exists else "new CI workflow/config"
    if (base == "dockerfile" or base.startswith("dockerfile.")
            or base.startswith("docker-compose.") or base in ("compose.yml", "compose.yaml")):
        # exact name or dot-suffixed family only — dockerfile_gen.py is a helper,
        # not a container config (wrongful-deny candidate flagged by re-verification)
        return "container build/deploy config"
    return None


def packet_active(root):
    """Any subdirectory of sdd-plus/changes/ that carries a tasks.md counts —
    kebab or not (bare-decoy dirs without artifacts do not)."""
    changes = root / "sdd-plus" / "changes"
    try:
        for p in changes.iterdir():
            try:
                if p.is_dir() and (p / "tasks.md").is_file():
                    return True
            except OSError:
                continue
    except OSError:
        pass
    return False


def _mark_warned(root, sid):
    """Persist warned=True. Returns True only if durably persisted (warn is
    spoken only then — a state failure degrades to silence, never nagging)."""
    if sid is None:
        return False
    path = state_path(sid)
    if path is None:
        return False
    state = read_state(path, sid)
    if state is None:
        state = new_state(sid, fingerprint_project(root))  # self-heal, like the Stop gate
    if state.get("warned"):
        return False  # already warned this session
    updated = dict(state)  # copy-and-update: preserve keys other hooks own
    updated["warned"] = True
    return write_state(path, updated)


def classify(data):
    """Return (decision, payload): ('silent', None) | ('warn', root) |
    ('deny', (label, root)) — deny carries the root so main() can ledger it."""
    tool = data.get("tool_name")
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd")
    if not isinstance(cwd, str) or not cwd or not os.path.isabs(cwd) or not os.path.isdir(cwd):
        return ("silent", None)

    if tool in ("Write", "Edit", "MultiEdit"):
        raw = tool_input.get("file_path") or tool_input.get("path") or ""
        targets = [raw] if isinstance(raw, str) and raw else []
        bash = False
    elif tool == "Bash":
        cmd = tool_input.get("command", "")
        targets = [t for t in bash_write_targets(cmd) if isinstance(t, str) and t]
        bash = True
    else:
        return ("silent", None)
    if not targets:
        return ("silent", None)

    plugin_root = plugin_root_from_env()
    cwd_root = find_drydock_root(Path(cwd), plugin_root)

    warn_root = None
    for raw_target in targets[:20]:
        target = _norm(raw_target, cwd)
        root = cwd_root
        if root is None or not _inside(target, root):
            # target-anchored fallback: a session parked outside the project must
            # not uncover writes INTO a Drydock project.
            root = find_drydock_root(target.parent, plugin_root)
        if root is None or not _inside(target, root):
            continue  # outside any Drydock project -> not ours to govern
        if (target.name.casefold() == "owner_status.md"
                and not _SOFT_SEGMENTS.intersection(_rel_parts(target, root))):
            # Generated artifact: hand-editing would let the status lie. Checked
            # BEFORE the .md exemption and regardless of packet state — no packet
            # makes freelancing the Owner surface governed work. The engine's own
            # --write-status is script-internal I/O the guard never sees.
            return ("deny", ("status-file", root))
        if is_exempt(target, root):
            continue
        if packet_active(root):
            continue  # governed session
        label = is_high_risk(target, root)
        if label:
            return ("deny", (label, root))
        if not bash:
            warn_root = root  # warn tier is Write/Edit only, by design
    return ("warn", warn_root) if warn_root is not None else ("silent", None)


DENY_REASON = (
    "Drydock packet guard: this write touches a high-impact path ({label}) and no "
    "change packet is active. High-impact work must run governed: create a packet "
    "first — python3 scripts/sdd.py new <kebab-name> (Windows: python) or /drydock:new — "
    "then retry this exact change. Do not work around this with shell redirection; "
    "if the Owner explicitly says to skip governance, they can disable the guard."
)

STATUS_DENY_REASON = (
    "Drydock packet guard: OWNER_STATUS.md is a generated snapshot authored by the "
    "brief engine — hand-editing it would let the Owner's status surface lie. "
    "Regenerate it with /drydock:brief. If the Owner wants it gone, they can delete "
    "or gitignore it themselves."
)

_DENY_CATEGORY = {
    "schema migration": "packet-deny:migration",
    "new CI workflow/config": "packet-deny:new-ci",
    "container build/deploy config": "packet-deny:container-config",
    "status-file": "packet-deny:status-file",
}

WARN_NOTE = (
    "[Drydock] Note (once per session): this session is editing project source with no "
    "active change packet. Trivial LITE edits are fine ungoverned; for meaningful work, "
    "open a packet with /drydock:new so specs, verification, and the archive trail exist. "
    "This note does not repeat."
)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            return 0
        decision, payload = classify(data)
        if decision == "deny":
            label, root = payload
            reason = STATUS_DENY_REASON if label == "status-file" else DENY_REASON.format(label=label)
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}))
            sys.stdout.flush()
            append_event(root, "packet_guard", "deny", _DENY_CATEGORY.get(label, "other"))
        elif decision == "warn":
            sid = sanitize_sid(data.get("session_id"))
            if _mark_warned(payload, sid):
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": WARN_NOTE,
                }}))
                sys.stdout.flush()
                append_event(payload, "packet_guard", "warn", "packet-warn")
    except BaseException:
        return 0  # never break an edit; silent-allow is the fail direction
    return 0


if __name__ == "__main__":
    sys.exit(main())
