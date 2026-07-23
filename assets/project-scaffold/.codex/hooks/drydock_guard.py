#!/usr/bin/env python3
"""Codex PreToolUse enforcement bridge for Drydock (SDD+).

Makes Drydock's deterministic deny-guards fire under Codex, using the SAME
`permissionDecision: deny` protocol the plugin already emits. It resolves the
installed Drydock plugin's `hooks/` (single source of truth) and reuses
`protect_secrets` + `git_safety` unchanged — Codex's hook payload is
Claude-compatible (`tool_name` + `tool_input`, shell command as `tool_input.command`).

Covers the stateless critical floor: destructive git + secret-bearing writes,
across shell tools (Bash/PowerShell) and Codex's native `apply_patch`.

FAILS OPEN (exit 0, no output) on ANY error — a guardrail bug must never brick a
Codex session. The agent-agnostic git pre-commit hook is the secrets backstop.
"""
import glob
import json
import os
import re
import sys

_EDIT_TOOLS = {"write", "edit", "multiedit"}


def _resolve_hooks_dir():
    """Find the Drydock plugin `hooks/` dir (with `_drydock_common.py`), or None."""
    # 1. Explicit override (tests / advanced installs).
    env = os.environ.get("DRYDOCK_HOOKS_DIR")
    if env and os.path.isfile(os.path.join(env, "_drydock_common.py")):
        return env
    # 2. CLAUDE_PLUGIN_ROOT (set when Claude runs; usually absent under Codex).
    pr = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if pr:
        h = os.path.join(pr, "hooks")
        if os.path.isfile(os.path.join(h, "_drydock_common.py")):
            return h
    # 3. Repo-local hooks/ (dogfooding inside the Drydock repo itself).
    cur = os.getcwd()
    for _ in range(6):
        h = os.path.join(cur, "hooks")
        if os.path.isfile(os.path.join(h, "_drydock_common.py")):
            return h
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    # 4. Installed plugin cache (newest version), then the marketplace clone.
    home = os.path.expanduser("~")
    cands = glob.glob(os.path.join(home, ".claude", "plugins", "cache", "drydock",
                                   "drydock", "*", "hooks", "_drydock_common.py"))
    if cands:
        return os.path.dirname(max(cands, key=os.path.getmtime))
    mk = os.path.join(home, ".claude", "plugins", "marketplaces", "drydock", "hooks")
    if os.path.isfile(os.path.join(mk, "_drydock_common.py")):
        return mk
    return None


def _apply_patch_paths(ti):
    """Best-effort target-path extraction from a Codex apply_patch tool_input.
    Covers the apply-patch text format and object/field shapes."""
    paths = set()
    for key in ("input", "patch", "content", "diff", "unified_diff"):
        v = ti.get(key)
        if isinstance(v, str):
            for m in re.finditer(r'^\*\*\*\s+(?:Add|Update|Delete) File:\s*(.+?)\s*$', v, re.M):
                paths.add(m.group(1).strip())
            for m in re.finditer(r'^\*\*\*\s+Move to:\s*(.+?)\s*$', v, re.M):
                paths.add(m.group(1).strip())
    for key in ("fileChanges", "changes", "files"):
        v = ti.get(key)
        if isinstance(v, dict):
            paths.update(k for k in v.keys() if isinstance(k, str))
    for key in ("file_path", "path", "move_path"):
        v = ti.get(key)
        if isinstance(v, str) and v:
            paths.add(v)
    return {p for p in paths if p}


def _command_string(ti):
    cmd = ti.get("command")
    if isinstance(cmd, list):
        return " ".join(str(x) for x in cmd)
    return cmd if isinstance(cmd, str) else ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # malformed input -> fail open
    if not isinstance(payload, dict):
        return 0
    try:
        hooks_dir = _resolve_hooks_dir()
        if not hooks_dir:
            return 0  # can't reach the guards -> fail open (git pre-commit backstops secrets)
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        import git_safety
        import protect_secrets
        from _drydock_common import command_write_targets, emit_permission_deny

        tool = payload.get("tool_name") or ""
        tl = tool.lower()
        ti = payload.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        reason = None

        if tl in _EDIT_TOOLS:
            # Case-robust: check the extracted path directly rather than relying on
            # protect_secrets.check's case-sensitive tool_name match.
            path = ti.get("file_path") or ti.get("path") or ""
            if isinstance(path, str) and protect_secrets.path_is_secret(path):
                reason = (f"'{path}' looks like a secrets/credentials file. Agents must not "
                          "create or edit secret-bearing files. Ask the Owner to handle it manually.")
        elif tl == "apply_patch":
            for p in _apply_patch_paths(ti):
                if protect_secrets.path_is_secret(p):
                    reason = (f"'{p}' looks like a secrets/credentials file. Agents must not "
                              "create or edit secret-bearing files. Ask the Owner to handle it manually.")
                    break
        else:  # shell tool (Bash/PowerShell/shell/...) -> command string
            cmd = _command_string(ti)
            if cmd.strip():
                reason = git_safety.check_command(cmd)  # destructive git
                if not reason:
                    # shell-name-agnostic: check both interpretations for secret writes
                    targets = set(command_write_targets(cmd, "Bash")) | \
                        set(command_write_targets(cmd, "PowerShell"))
                    for t in targets:
                        if protect_secrets.path_is_secret(t):
                            reason = (f"this command writes to '{t}', which looks like a secrets/"
                                      "credentials file. Agents must not create or edit secret-bearing files.")
                            break

        if reason:
            emit_permission_deny(f"Blocked by SDD+ (Codex bridge): {reason}")
            return 0
    except Exception:
        return 0  # any guard error -> fail open
    return 0


if __name__ == "__main__":
    sys.exit(main())
