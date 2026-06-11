#!/usr/bin/env python3
"""PreToolUse hook: require Owner confirmation for destructive git commands.

Reads tool-call JSON from stdin. Exit 2 blocks the call and feeds stderr back
to the agent. Exit 0 allows it. Conservative by design: only fires on commands
that can destroy committed or uncommitted work.
"""
import json
import re
import sys

DESTRUCTIVE = [
    (re.compile(r"\bgit\s+push\b(?!.*--force-with-lease).*(\s--force\b|\s-f\b)"),
     "force push (use --force-with-lease, or get the Owner's explicit approval)"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "hard reset (discards uncommitted work)"),
    (re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f"), "git clean -f (deletes untracked files)"),
    (re.compile(r"\bgit\s+branch\s+(-D|--delete\s+--force)\b"), "force-delete branch"),
    (re.compile(r"\bgit\s+checkout\s+--\s+\."), "checkout -- . (discards all local changes)"),
    (re.compile(r"\bgit\s+restore\s+(?!--staged)\."), "restore . (discards all local changes)"),
    (re.compile(r"\bgit\s+stash\s+(drop|clear)\b"), "stash drop/clear (deletes stashed work)"),
]

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the session on malformed input
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if not command:
        return 0
    for pattern, label in DESTRUCTIVE:
        if pattern.search(command):
            print(
                f"Blocked by Drydock git-safety guardrail: this command performs a {label}. "
                "Destructive git operations require the Owner's explicit approval in chat. "
                "Explain what you want to do and why, then proceed only if the Owner approves "
                "(they can run it themselves or tell you to bypass this check for one command).",
                file=sys.stderr,
            )
            return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
