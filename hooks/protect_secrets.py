#!/usr/bin/env python3
"""PreToolUse hook: block agent writes to secret-bearing paths.

Reads the tool-call JSON from stdin. Exit code 2 blocks the tool call and
feeds stderr back to the agent as the reason. Exit code 0 allows it.

Covers Write/Edit/MultiEdit targets AND Bash commands that write to a secret
path (redirections, tee, cp/mv destinations). Example/template env files are
explicitly allowed, matching the scaffold .gitignore's `!.env.example`.
"""
import json
import re
import shlex
import sys

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


def _bash_write_targets(command):
    """Best-effort set of paths a Bash command writes to (redirections, tee, cp/mv)."""
    targets = []
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:  # unbalanced quotes -> regex-only fallback below
        tokens = []
    for i, tok in enumerate(tokens):
        if tok in (">", ">>", "1>", "2>", "&>", ">|") and i + 1 < len(tokens):
            targets.append(tokens[i + 1])
        elif re.match(r"^\d*>>?\|?", tok) and len(tok) > tok.rstrip(">|").__len__():
            # attached redirection like >.env or >>.env
            targets.append(re.sub(r"^\d*>>?\|?", "", tok))
        elif tok == "tee":
            for nxt in tokens[i + 1:]:
                if not nxt.startswith("-"):
                    targets.append(nxt)
                    break
        elif tok in ("cp", "mv") and len(tokens) > i + 2:
            targets.append(tokens[-1])  # destination is the last argument
    # regex fallback catches redirections even if tokenization failed
    for m in re.finditer(r">>?\|?\s*([^\s;|&>]+)", command):
        targets.append(m.group(1))
    return targets


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
    if tool_name in (None, "Bash"):
        command = tool_input.get("command", "")
        for target in _bash_write_targets(command):
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
        print(f"Blocked by SDD+ secrets guardrail: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
