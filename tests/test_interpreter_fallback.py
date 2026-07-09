"""The headline regression for the `||`-deny-swallow bug.

Runs the ACTUAL `<py> X || <py> X` chain (the shape hooks.json uses) with a
destructive payload and asserts the deny reaches STDOUT and the chain exits 0.

Both interpreters are the SAME working Python — precisely the scenario that
triggered the bug: python3 works, the first process runs, and an exit-2 deny
was swallowed by the `||` fallback re-running on drained stdin (its block was on
stderr and the fallback allowed on empty input, so the chain's stdout was empty
and its exit was 0 → ALLOW). With the JSON-deny protocol the first process
exits 0, the fallback never fires, and the deny is on stdout. This test would
have caught the original bug (stdout would be empty).
"""
import json
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


def _chain(guard_name, payload):
    guard = HOOKS / guard_name
    py = sys.executable
    cmd = f'"{py}" "{guard}" || "{py}" "{guard}"'
    return subprocess.run(cmd, shell=True, input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, timeout=30)


def test_git_safety_deny_survives_the_or_fallback():
    r = _chain("git_safety.py",
               {"tool_name": "Bash", "tool_input": {"command": "git reset --hard"}})
    assert r.returncode == 0
    assert b'"permissionDecision": "deny"' in r.stdout
    assert r.stdout.count(b'"permissionDecision"') == 1  # the fallback did NOT re-run


def test_secrets_deny_survives_the_or_fallback():
    r = _chain("protect_secrets.py",
               {"tool_name": "Write", "tool_input": {"file_path": ".env"}})
    assert r.returncode == 0
    assert b'"permissionDecision": "deny"' in r.stdout
    assert r.stdout.count(b'"permissionDecision"') == 1


def test_powershell_git_deny_survives_the_or_fallback():
    r = _chain("git_safety.py",
               {"tool_name": "PowerShell", "tool_input": {"command": "git push --force origin main"}})
    assert r.returncode == 0
    assert b'"permissionDecision": "deny"' in r.stdout


def test_git_exe_is_detected():
    # git.exe is the canonical Windows/PowerShell invocation — must not bypass
    r = _chain("git_safety.py",
               {"tool_name": "PowerShell", "tool_input": {"command": "git.exe reset --hard"}})
    assert r.returncode == 0
    assert b'"permissionDecision": "deny"' in r.stdout


def test_powershell_native_secret_deny_survives_the_or_fallback():
    r = _chain("protect_secrets.py",
               {"tool_name": "PowerShell", "tool_input": {"command": "Set-Content -Path .env -Value x"}})
    assert r.returncode == 0
    assert b'"permissionDecision": "deny"' in r.stdout


def test_benign_passes_the_chain_silently():
    r = _chain("git_safety.py",
               {"tool_name": "Bash", "tool_input": {"command": "git status"}})
    assert r.returncode == 0
    assert b'"deny"' not in r.stdout
