#!/usr/bin/env python3
"""PreToolUse hook: block agent writes to secret-bearing paths.

Reads the tool-call JSON from stdin. Denies via the PreToolUse JSON
permissionDecision protocol (exit 0) — never exit 2, which the `python3 X ||
python X` wrapper reads as launch failure and swallows by re-running on drained
stdin. Exit 0 with no output allows.

Covers Write/Edit/MultiEdit targets AND Bash/PowerShell commands that write to a
secret path (POSIX redirections/tee/cp/mv, plus PowerShell-native cmdlets like
Set-Content/Out-File/Copy-Item). Example/template env files are explicitly
allowed, matching the scaffold .gitignore's `!.env.example`.
"""
import json
import os
import re
import sys
from pathlib import Path

from _drydock_common import (append_event, command_write_targets, emit_permission_deny,
                             find_drydock_root, plugin_root_from_env)

# Basenames that look secret but are documentation templates -> always allowed.
_ALLOW_BASENAMES = {".env.example", ".env.template", ".env.sample"}

# Secret-bearing path patterns, matched against the basename (case-insensitive).
_SECRET = re.compile(
    r"""^(
        \.env(\..+)?              # .env, .env.local, .env.production
        | .+\.env                 # prod.env, staging.env
        | \.envrc
        | .+\.pem
        | .+\.key
        | id_(rsa|dsa|ecdsa|ed25519)(\..+)?   # ssh private keys incl. modern default
        | .+\.(ppk|p12|pfx|jks)   # putty key + keystores
        | credentials(\..+)?
        | secrets?\.(json|ya?ml|toml)
        | service[-_]account.*\.json
    )$""",
    re.IGNORECASE | re.VERBOSE,
)


def path_is_secret(path):
    if not path:
        return False
    basename = path.replace("\\", "/").rstrip("/").split("/")[-1]
    if basename.lower() in _ALLOW_BASENAMES:
        return False
    return bool(_SECRET.match(basename))


def check(tool_name, tool_input):
    """Return a reason string if this call writes a secret path, else None."""
    tool_input = tool_input or {}
    if tool_name in (None, "Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path") or tool_input.get("path") or ""
        if path_is_secret(path):
            return (
                f"'{path}' looks like a secrets/credentials file. Agents must not create "
                "or edit secret-bearing files. Ask the Owner to handle this file manually."
            )
    if tool_name in (None, "Bash", "PowerShell"):
        command = tool_input.get("command", "")
        for target in command_write_targets(command, tool_name or "Bash"):
            if path_is_secret(target):
                return (
                    f"this command writes to '{target}', which looks like a secrets/credentials "
                    "file. Agents must not create or edit secret-bearing files. Ask the Owner "
                    "to handle it manually."
                )
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the session on malformed input
    reason = check(payload.get("tool_name"), payload.get("tool_input"))
    if reason:
        emit_permission_deny(f"Blocked by SDD+ secrets guardrail: {reason}")  # JSON deny, exit 0
        _record_deny(payload)  # best-effort telemetry, strictly after the verdict
        return 0
    return 0


def _record_deny(payload):
    """Ledger append for the Owner brief. Never raises, never fsyncs, cannot
    change the verdict above (which is already written and flushed)."""
    try:
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not cwd or not os.path.isabs(cwd) or not os.path.isdir(cwd):
            return
        root = find_drydock_root(Path(cwd), plugin_root_from_env())
        if root is not None:
            append_event(root, "protect_secrets", "deny", "secrets-deny")
    except BaseException:
        return


if __name__ == "__main__":
    sys.exit(main())
