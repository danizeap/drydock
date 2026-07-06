"""Behavioral tests for the destructive-git guardrail.

Encodes the git-safety-hook delta spec: every audit bypass is a must-block case,
every confirmed false positive is a must-allow case.
"""
import pytest

import git_safety

# --- must block (destructive) ---------------------------------------------
BLOCK = [
    # baseline
    "git reset --hard HEAD~1",
    "git reset --hard",
    # global-flag prefix bypass (audit HIGH)
    "git -C . reset --hard",
    "git -c core.pager=cat reset --hard",
    "git --git-dir=/r/.git reset --hard",
    # quoting bypass (audit HIGH)
    "git reset '--hard'",
    "git reset \"--hard\"",
    # compound commands inspected per segment
    "echo done && git reset --hard",
    "true; git clean -fd",
    # checkout/switch/restore working-tree discards (audit HIGH)
    "git checkout .",
    "git checkout -- .",
    "git checkout -f",
    "git switch -f main",
    "git switch --discard-changes main",
    "git restore .",
    "git restore --worktree .",
    # clean force variants
    "git clean -f",
    "git clean -fd",
    "git clean -d -f",
    "git clean --force",
    "git clean -xdf",
    # remote destruction
    "git push origin +main",
    "git push --force origin main",
    "git push -f",
    "git push --mirror origin",
    "git push --force-with-lease --force origin main",
    "git push --delete origin feature",
    "git push origin :feature",
    # history/ref destruction
    "git branch -D feature",
    "git update-ref -d refs/heads/main",
    "git reflog expire --expire=now --all",
    "git worktree remove --force wt",
    # stash
    "git stash drop",
    "git stash clear",
    # unparseable -> fallback still guards
    'git reset --hard "oops',
]

# --- must allow (legitimate) ----------------------------------------------
ALLOW = [
    # quoted mention of a destructive string in a message (audit false positive)
    'git commit -m "revert the reset --hard incident"',
    'git commit -m "cleanup: git clean -fd notes"',
    # sanctioned safe forms
    "git restore --staged .",
    "git push --force-with-lease origin main",
    "git push --force-with-lease=main origin main",
    "git branch -d merged-branch",
    "git checkout feature-branch",
    "git checkout -b new-branch",
    "git switch main",
    "git clean -n",
    "git clean -nd",
    "git reset HEAD~1",
    "git reset --soft HEAD~1",
    # ordinary read/write commands
    "git status",
    "git log --oneline -5",
    "git push origin main",
    "git add -A",
    "git commit -m message",
    "npm run build",
    "echo hello world",
    "",
]


@pytest.mark.parametrize("cmd", BLOCK)
def test_blocks_destructive(cmd):
    assert git_safety.check_command(cmd) is not None, f"should BLOCK: {cmd!r}"


@pytest.mark.parametrize("cmd", ALLOW)
def test_allows_legitimate(cmd):
    assert git_safety.check_command(cmd) is None, f"should ALLOW: {cmd!r}"


def test_block_message_makes_no_phantom_bypass_promise():
    reason = git_safety.check_command("git reset --hard")
    assert reason
    msg = git_safety.block_message(reason).lower()
    assert "owner" in msg
    # the old message promised a per-command bypass that has no mechanism
    assert "bypass this check for one command" not in msg


def test_malformed_payload_never_crashes(capsys):
    import io
    import sys
    old = sys.stdin
    sys.stdin = io.StringIO("not json")
    try:
        assert git_safety.main() == 0
    finally:
        sys.stdin = old
