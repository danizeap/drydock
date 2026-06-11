#!/usr/bin/env python3
"""PreToolUse hook: block agent edits to secret-bearing paths.

Reads the tool-call JSON from stdin. Exit code 2 blocks the tool call and
feeds stderr back to the agent as the reason. Exit code 0 allows it.
"""
import json
import re
import sys

BLOCKED = re.compile(
    r"(^|/)(\.env(\..+)?|.+\.pem|.+\.key|id_rsa.*|credentials(\..+)?|secrets?\.(json|ya?ml|toml))$",
    re.IGNORECASE,
)

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the session on malformed input
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if path and BLOCKED.search(path.replace("\\", "/")):
        print(
            f"Blocked by SDD+ secrets guardrail: '{path}' looks like a secrets/credentials "
            "file. Agents must not create or edit secret-bearing files. Ask the Owner to "
            "handle this file manually.",
            file=sys.stderr,
        )
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
