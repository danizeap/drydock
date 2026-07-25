"""Deterministic fake for process-runner contract tests."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path


def _argument(name: str) -> str | None:
    try:
        return sys.argv[sys.argv.index(name) + 1]
    except (ValueError, IndexError):
        return None


def main() -> int:
    prompt = sys.stdin.read()
    log = os.environ.get("DRYDOCK_FAKE_LOG")
    if log:
        Path(log).write_text(
            json.dumps(
                {
                    "argv": sys.argv[1:],
                    "prompt": prompt,
                    "poison_gitdir": os.environ.get(
                        "DRYDOCK_FAKE_POISON_GITDIR"
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    sleep = float(os.environ.get("DRYDOCK_FAKE_SLEEP", "0"))
    if sleep:
        time.sleep(sleep)
    root_value = _argument("-C")
    if root_value and os.environ.get("DRYDOCK_FAKE_MUTATE") == "1":
        (Path(root_value) / "worker.py").write_text(
            "print('worker change')\n", encoding="utf-8"
        )
    if root_value and os.environ.get("DRYDOCK_FAKE_TEXT") == "1":
        (Path(root_value) / "notes.txt").write_text(
            "text-only change\n", encoding="utf-8"
        )
    if root_value and os.environ.get("DRYDOCK_FAKE_IGNORED") == "1":
        ignored = Path(root_value) / "ignored-worker.txt"
        (Path(root_value) / ".gitignore").write_text(
            ".drydock-worktrees/\nignored-worker.txt\n",
            encoding="utf-8",
        )
        ignored.write_text("ignored worker artifact\n", encoding="utf-8")
    if root_value and os.environ.get("DRYDOCK_FAKE_ATTRIBUTES") == "1":
        (Path(root_value) / ".gitattributes").write_text(
            "worker.py -diff\n", encoding="utf-8"
        )
    poison = os.environ.get("DRYDOCK_FAKE_POISON_GITDIR")
    if root_value and poison:
        link = Path(root_value) / ".git"
        if os.name == "nt":
            subprocess.run(
                ["attrib", "-H", str(link)],
                check=True,
                capture_output=True,
            )
        link.chmod(stat.S_IWRITE | stat.S_IREAD)
        if poison == "delete":
            link.unlink()
        else:
            link.write_text(f"gitdir: {poison}\n", encoding="utf-8")
            if os.environ.get("DRYDOCK_FAKE_RECORD_POISON") == "1":
                (Path(root_value) / "poison-observed.txt").write_text(
                    link.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
    poison_config = os.environ.get("DRYDOCK_FAKE_POISON_GIT_CONFIG")
    if poison_config:
        fsmonitor = os.environ.get("DRYDOCK_FAKE_FSMONITOR", "false")
        hooks_path = os.environ.get("DRYDOCK_FAKE_HOOKS_PATH", os.devnull)
        with Path(poison_config).open(
            "a", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(
                "\n[core]\n"
                f"\tfsmonitor = {json.dumps(Path(fsmonitor).as_posix())}\n"
                f"\thooksPath = {json.dumps(Path(hooks_path).as_posix())}\n"
            )
    if root_value and os.environ.get("DRYDOCK_FAKE_BACKGROUND") == "1":
        late = Path(root_value) / "late-background.txt"
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import pathlib,time;"
                    "time.sleep(2);"
                    f"pathlib.Path({str(late)!r}).write_text("
                    "'late write\\n',encoding='utf-8')"
                ),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    owner_path = os.environ.get("DRYDOCK_FAKE_OWNER_PATH")
    if owner_path:
        Path(owner_path).write_text("owner drift\n", encoding="utf-8")
    if root_value and os.environ.get("DRYDOCK_FAKE_COMMIT") == "1":
        subprocess.run(["git", "add", "-A"], cwd=root_value, check=True)
        subprocess.run(
            ["git", "commit", "-m", "worker must not commit"],
            cwd=root_value,
            check=True,
            capture_output=True,
        )
    output = _argument("--output-last-message")
    if output:
        schema_path = _argument("--output-schema")
        state_binding = {}
        if schema_path:
            schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
            properties = schema["properties"]["state_binding"]["properties"]
            state_binding = {
                "head": properties["head"]["const"],
                "working_tree_sha256": properties[
                    "working_tree_sha256"
                ]["const"],
            }
        verdict = {
            "verdict": os.environ.get("DRYDOCK_FAKE_VERDICT", "PASS"),
            "summary": "fake verifier result",
            "findings": [],
            "checks": ["fake deterministic check"],
            "state_binding": state_binding,
        }
        if os.environ.get("DRYDOCK_FAKE_BAD_CHECK") == "1":
            verdict["checks"] = [1]
        if os.environ.get("DRYDOCK_FAKE_BAD_BINDING") == "1":
            verdict["state_binding"]["head"] = "wrong"
        Path(output).write_text(json.dumps(verdict), encoding="utf-8")
    print(json.dumps({"type": "result", "ok": True}))
    return int(os.environ.get("DRYDOCK_FAKE_EXIT", "0"))


if __name__ == "__main__":
    raise SystemExit(main())
