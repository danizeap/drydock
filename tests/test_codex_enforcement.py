"""Tests for the Codex enforcement bridge.

Replays Codex-shaped PreToolUse payloads through the scaffolded dispatcher
(`assets/project-scaffold/.codex/hooks/drydock_guard.py`) as a subprocess, with
`DRYDOCK_HOOKS_DIR` pointed at the repo's own `hooks/` so the guards resolve.
Also exercises the agent-agnostic git pre-commit backstop.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "assets", "project-scaffold", ".codex", "hooks", "drydock_guard.py")
HOOKS = os.path.join(ROOT, "hooks")
PRECOMMIT = os.path.join(ROOT, "assets", "project-scaffold", "hooks", "git", "pre-commit")


def run_guard(payload, raw=None):
    env = dict(os.environ)
    env["DRYDOCK_HOOKS_DIR"] = HOOKS
    data = raw if raw is not None else json.dumps(payload)
    return subprocess.run([sys.executable, GUARD], input=data,
                          capture_output=True, text=True, env=env)


def is_deny(p):
    if p.returncode != 0 or not p.stdout.strip():
        return False
    try:
        j = json.loads(p.stdout.strip())
    except Exception:
        return False
    hso = j.get("hookSpecificOutput", {})
    return hso.get("hookEventName") == "PreToolUse" and hso.get("permissionDecision") == "deny"


# ---- denies (exit 0 + JSON deny) ----
def test_destructive_git_denied():
    p = run_guard({"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~3"}})
    assert is_deny(p) and p.returncode == 0


def test_shell_secret_redirect_denied():
    p = run_guard({"tool_name": "Bash", "tool_input": {"command": "echo SECRET=1 > .env"}})
    assert is_deny(p)


def test_powershell_native_secret_write_denied():
    p = run_guard({"tool_name": "PowerShell",
                   "tool_input": {"command": "Set-Content -Path .env -Value 'K=V'"}})
    assert is_deny(p)


def test_apply_patch_creating_secret_denied():
    patch = "*** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n"
    p = run_guard({"tool_name": "apply_patch", "tool_input": {"input": patch}})
    assert is_deny(p)


def test_write_tool_secret_denied():
    p = run_guard({"tool_name": "Write", "tool_input": {"file_path": "config/prod.env"}})
    assert is_deny(p)


def test_lowercase_edit_tool_secret_denied():
    # Case-robust: a lowercased edit tool name must still catch a secret path.
    p = run_guard({"tool_name": "write", "tool_input": {"file_path": ".env"}})
    assert is_deny(p)


def test_command_argv_array_denied():
    # Codex may present a command as an argv array; the dispatcher joins it.
    p = run_guard({"tool_name": "Bash", "tool_input": {"command": ["git", "reset", "--hard"]}})
    assert is_deny(p)


# ---- allows (silent, exit 0, no output) ----
def test_benign_command_silent():
    p = run_guard({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_benign_write_silent():
    p = run_guard({"tool_name": "Write", "tool_input": {"file_path": "src/app.py"}})
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_apply_patch_benign_silent():
    patch = "*** Begin Patch\n*** Add File: notes.txt\n+hello\n*** End Patch\n"
    p = run_guard({"tool_name": "apply_patch", "tool_input": {"input": patch}})
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_reading_secret_stays_allowed():
    p = run_guard({"tool_name": "Bash", "tool_input": {"command": "cat .env"}})
    assert p.returncode == 0 and p.stdout.strip() == ""


# ---- fail-open ----
def test_malformed_input_fails_open():
    p = run_guard(None, raw="not json {{{")
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_unresolvable_plugin_fails_open(tmp_path):
    # DRYDOCK_HOOKS_DIR points nowhere and cwd is outside any repo/plugin tree.
    env = dict(os.environ)
    env["DRYDOCK_HOOKS_DIR"] = str(tmp_path / "nope")
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    p = subprocess.run([sys.executable, GUARD],
                       input=json.dumps({"tool_name": "Bash",
                                         "tool_input": {"command": "git reset --hard"}}),
                       capture_output=True, text=True, env=env, cwd=str(tmp_path))
    assert p.returncode == 0 and p.stdout.strip() == ""


# ---- agent-agnostic git pre-commit backstop ----
def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def _init_repo(path):
    _git(["init"], path)
    _git(["config", "user.email", "t@example.com"], path)
    _git(["config", "user.name", "Test"], path)


def test_precommit_blocks_staged_secret(tmp_path):
    repo = str(tmp_path)
    _init_repo(repo)
    with open(os.path.join(repo, ".env"), "w") as f:
        f.write("SECRET=1")
    _git(["add", ".env"], repo)
    p = subprocess.run([sys.executable, PRECOMMIT], cwd=repo, capture_output=True, text=True)
    assert p.returncode == 1 and ".env" in p.stderr


def test_precommit_allows_normal_file(tmp_path):
    repo = str(tmp_path)
    _init_repo(repo)
    with open(os.path.join(repo, "README.md"), "w") as f:
        f.write("# hi")
    _git(["add", "README.md"], repo)
    p = subprocess.run([sys.executable, PRECOMMIT], cwd=repo, capture_output=True, text=True)
    assert p.returncode == 0
