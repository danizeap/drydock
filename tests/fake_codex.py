#!/usr/bin/env python3
"""Fake Codex CLI for tests — no network, no quota, no account.

Emulates just enough of the real CLI for the conductor bridge:
  app-server : JSON-RPC handshake over stdio -> canned account/rateLimits/read
  exec       : JSONL events on stdout + writes a canned result to
               --output-last-message

Behaviour tweaks via FAKE_CODEX_MODE:
  normal (default) | early_exit | timeout | nonobject | exit_after_init
"""
import json
import os
import subprocess
import sys
import time

MODE = os.environ.get("FAKE_CODEX_MODE", "normal")

RATE = {"rateLimits": {
    "limitId": "codex",
    "primary": {"usedPercent": 5, "windowDurationMins": 10080, "resetsAt": 1785280681},
    "secondary": None,
    "credits": {"hasCredits": False, "unlimited": False, "balance": "0"},
    "planType": "plus",
}}

RESULT = {"overall_assessment": "FAKE_OK", "findings": []}


def out(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def app_server():
    if MODE == "early_exit":
        sys.exit(1)
    while True:
        line = sys.stdin.readline()
        if not line:
            return
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if not isinstance(msg, dict):
            continue
        mid, method = msg.get("id"), msg.get("method")
        if method == "initialize":
            out({"jsonrpc": "2.0", "id": mid, "result": {"capabilities": {}}})
            if MODE == "exit_after_init":
                sys.exit(0)
        elif method == "account/rateLimits/read":
            if MODE == "timeout":
                time.sleep(5)  # caller with a short timeout will have given up
            if MODE == "nonobject":
                out(123)       # a non-dict line the reader MUST ignore
            out({"jsonrpc": "2.0", "id": mid, "result": RATE})
            return
        # notifications (e.g. "initialized") and anything else: ignore


def exec_cmd(argv):
    sys.stdin.read()  # consume the prompt
    out_file = None
    for i, a in enumerate(argv):
        if a == "--output-last-message" and i + 1 < len(argv):
            out_file = argv[i + 1]
    out({"type": "thread.started", "thread_id": "fake-thread"})
    out({"type": "turn.started"})
    out({"type": "item.completed",
         "item": {"type": "agent_message", "text": json.dumps(RESULT)}})
    out({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 5}})
    if out_file:
        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(RESULT, fh)


def sandbox_cmd(argv):
    """Model-free test double for `codex sandbox`.

    The real security boundary is proven by the live platform spike. This fake
    exists only so unit tests can assert that mutate routes through the boundary
    instead of executing the test command directly.
    """
    if "--help" in argv or "-h" in argv:
        print("fake codex sandbox")
        return 0
    cwd = None
    index = 0
    value_options = {
        "-c",
        "--config",
        "-P",
        "--permission-profile",
        "-p",
        "--profile",
        "-C",
        "--cd",
        "--sandbox-state-json",
        "--sandbox-state-readable-root",
        "--enable",
        "--disable",
    }
    flag_options = {
        "--sandbox-state-disable-network",
        "--include-managed-config",
    }
    while index < len(argv):
        argument = argv[index]
        if argument in value_options:
            if index + 1 >= len(argv):
                return 2
            if argument in {"-C", "--cd"}:
                cwd = argv[index + 1]
            index += 2
            continue
        if argument in flag_options:
            index += 1
            continue
        break
    command = argv[index:]
    if not command:
        return 2
    process = subprocess.run(command, cwd=cwd, shell=False)
    return process.returncode


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit(2)
    if argv[0] == "app-server":
        app_server()
    elif argv[0] == "exec":
        exec_cmd(argv)
    elif argv[0] == "sandbox":
        raise SystemExit(sandbox_cmd(argv[1:]))
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
