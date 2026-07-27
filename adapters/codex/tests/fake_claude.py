"""Deterministic fake Claude CLI for peer-adapter tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _log(prompt: str) -> None:
    path = os.environ.get("DRYDOCK_FAKE_CLAUDE_LOG")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {"argv": sys.argv[1:], "prompt": prompt, "cwd": os.getcwd()},
                separators=(",", ":"),
            )
            + "\n"
        )


def main() -> int:
    if sys.argv[1:4] == ["auth", "status", "--json"]:
        _log("")
        logged_in = os.environ.get("DRYDOCK_FAKE_CLAUDE_AUTH", "1") == "1"
        print(
            json.dumps(
                {
                    "loggedIn": logged_in,
                    "authMethod": "claude.ai" if logged_in else "none",
                    "apiProvider": "firstParty" if logged_in else None,
                    "subscriptionType": "max" if logged_in else None,
                }
            )
        )
        return 0 if logged_in else 1

    prompt = sys.stdin.read()
    _log(prompt)
    descendant_sentinel = os.environ.get(
        "DRYDOCK_FAKE_CLAUDE_DESCENDANT_SENTINEL"
    )
    if descendant_sentinel:
        delay = float(
            os.environ.get("DRYDOCK_FAKE_CLAUDE_DESCENDANT_DELAY", "2.5")
        )
        script = (
            "import pathlib,sys,time;"
            "time.sleep(float(sys.argv[2]));"
            "pathlib.Path(sys.argv[1]).write_text('escaped', encoding='utf-8')"
        )
        subprocess.Popen(
            [sys.executable, "-c", script, descendant_sentinel, str(delay)]
        )
    sleep = float(os.environ.get("DRYDOCK_FAKE_CLAUDE_SLEEP", "0"))
    if sleep:
        time.sleep(sleep)
    blockers = json.loads(os.environ.get("DRYDOCK_FAKE_CLAUDE_BLOCKERS", "[]"))
    critique: object = {
        "converged": os.environ.get("DRYDOCK_FAKE_CLAUDE_CONVERGED", "1") == "1",
        "overall": "fake peer assessment",
        "blocking_concerns": blockers,
        "gaps": [],
        "risks": [],
        "task_decomposition": [
            {
                "task": "bounded implementation",
                "owner": "codex",
                "model_tier": "workhorse",
                "rationale": "mechanical and reviewable",
            }
        ],
    }
    if os.environ.get("DRYDOCK_FAKE_CLAUDE_MALFORMED") == "1":
        critique = {"converged": True}
    model = os.environ.get("DRYDOCK_FAKE_CLAUDE_MODEL", "claude-opus-5")
    envelope = {
        "type": "result",
        "subtype": os.environ.get("DRYDOCK_FAKE_CLAUDE_SUBTYPE", "success"),
        "is_error": os.environ.get("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "0") == "1",
        "structured_output": critique,
        "total_cost_usd": float(os.environ.get("DRYDOCK_FAKE_CLAUDE_COST", "0.05")),
        "modelUsage": {model: {"inputTokens": 10, "outputTokens": 10}},
    }
    if os.environ.get("DRYDOCK_FAKE_CLAUDE_NO_MODEL_USAGE") == "1":
        envelope.pop("modelUsage")
    if os.environ.get("DRYDOCK_FAKE_CLAUDE_NO_COST") == "1":
        envelope.pop("total_cost_usd")
    if "DRYDOCK_FAKE_CLAUDE_RESULT" in os.environ:
        envelope["result"] = os.environ["DRYDOCK_FAKE_CLAUDE_RESULT"]
    if "DRYDOCK_FAKE_CLAUDE_ERROR_TYPE" in os.environ:
        envelope["error"] = {
            "type": os.environ["DRYDOCK_FAKE_CLAUDE_ERROR_TYPE"]
        }
    print(json.dumps(envelope))
    return int(os.environ.get("DRYDOCK_FAKE_CLAUDE_EXIT", "0"))


if __name__ == "__main__":
    raise SystemExit(main())
