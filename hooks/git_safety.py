#!/usr/bin/env python3
"""PreToolUse hook: require Owner confirmation for destructive git commands.

Reads tool-call JSON from stdin. Exit 2 blocks the call and feeds stderr back
to the agent. Exit 0 allows it. Conservative by design: only fires on commands
that can destroy committed or uncommitted work.

Matching is token-based (shlex), not substring-based: git global options
(-C, -c, --git-dir, ...) are skipped to find the real subcommand, so prefixes
like `git -C . reset --hard` cannot slip through, and destructive strings
quoted inside a commit message do not false-positive. If a command cannot be
tokenized (e.g. unbalanced quotes), we fall back to a legacy pattern scan so
the guard never fails open.
"""
import json
import re
import shlex
import sys

# git global options that take a separate argument (skip both tokens)
_GLOBAL_WITH_ARG = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path", "--config-env",
}
# git global options that take no argument (skip one token)
_GLOBAL_NO_ARG = {
    "-p", "--paginate", "-P", "--no-pager", "--bare",
    "--no-replace-objects", "--literal-pathspecs", "--no-literal-pathspecs",
    "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs", "--no-optional-locks",
}
# shell tokens that separate one command from the next
_SEPARATORS = {"&&", "||", ";", "|", "&", "|&"}

# legacy fallback patterns (used only when tokenization fails)
_LEGACY = [
    (re.compile(r"\bgit\b.*\breset\s+--hard\b"), "hard reset (discards uncommitted work)"),
    (re.compile(r"\bgit\b.*\bclean\s+-[a-zA-Z]*f"), "git clean -f (deletes untracked files)"),
    (re.compile(r"\bgit\b.*\bpush\b.*(--force\b|\s-f\b|--mirror\b)"), "force/mirror push"),
    (re.compile(r"\bgit\b.*\bcheckout\b.*(\s\.|\s--\s|\s-f\b)"), "checkout discard"),
    (re.compile(r"\bgit\b.*\bbranch\s+-D\b"), "force-delete branch"),
    (re.compile(r"\bgit\b.*\bstash\s+(drop|clear)\b"), "stash drop/clear"),
]


def _segments(tokens):
    """Split a flat token list into command segments on shell separators."""
    seg, out = [], []
    for t in tokens:
        if t in _SEPARATORS:
            if seg:
                out.append(seg)
            seg = []
        else:
            seg.append(t)
    if seg:
        out.append(seg)
    return out


def _subcommand_index(tokens, git_idx):
    """Index of the git subcommand after skipping global options, or None."""
    i = git_idx + 1
    while i < len(tokens):
        t = tokens[i]
        if t.startswith("--") and "=" in t:  # --git-dir=... inline arg
            i += 1
            continue
        if t in _GLOBAL_WITH_ARG:
            i += 2
            continue
        if t in _GLOBAL_NO_ARG:
            i += 1
            continue
        if t.startswith("-"):  # unknown global flag, skip conservatively
            i += 1
            continue
        return i
    return None


def _is_short_force(tok):
    """A combined short flag containing 'f' (e.g. -f, -fd, -xdf) but not a long flag."""
    return tok.startswith("-") and not tok.startswith("--") and "f" in tok[1:]


def _check_subcommand(sub, args):
    """Return a reason string if this git subcommand+args is destructive, else None."""
    a = args
    if sub == "reset":
        if "--hard" in a:
            return "hard reset (discards uncommitted work)"
    elif sub == "clean":
        if any(t == "--force" or _is_short_force(t) for t in a):
            return "git clean -f (deletes untracked files)"
    elif sub in ("checkout",):
        if "." in a or "*" in a or "-f" in a or "--force" in a:
            return "checkout discard (overwrites local changes)"
    elif sub == "switch":
        if "-f" in a or "--force" in a or "--discard-changes" in a:
            return "switch --force/--discard-changes (drops local changes)"
    elif sub == "restore":
        staged_only = ("--staged" in a) and ("--worktree" not in a)
        if ("." in a or "*" in a) and not staged_only:
            return "restore . (discards working-tree changes)"
    elif sub == "stash":
        if a[:1] and a[0] in ("drop", "clear"):
            return "stash drop/clear (deletes stashed work)"
    elif sub == "push":
        lease = any(t == "--force-with-lease" or t.startswith("--force-with-lease=") for t in a)
        plus_refspec = any(t.startswith("+") and not t.startswith("--") for t in a)
        colon_delete = any((":" in t) and t.split(":", 1)[0] == "" and not t.startswith("-") for t in a)
        force = ("--force" in a) or ("-f" in a) or ("--mirror" in a) or plus_refspec
        delete = ("--delete" in a) or ("-d" in a) or colon_delete
        if force or delete:
            # lease alone is the sanctioned safe form; only allow when no bare force/delete
            if lease and not (("--force" in a) or ("-f" in a) or ("--mirror" in a) or plus_refspec or delete):
                return None
            return "force/mirror/delete push (rewrites or removes remote history)"
    elif sub == "branch":
        if "-D" in a or ("--delete" in a and "--force" in a):
            return "force-delete branch (may discard unmerged commits)"
    elif sub == "update-ref":
        if "-d" in a or "--delete" in a:
            return "update-ref -d (deletes a ref)"
    elif sub == "reflog":
        if a[:1] == ["expire"] and any(t.startswith("--expire") and t.endswith("now") for t in a):
            return "reflog expire --expire=now (destroys recovery history)"
    elif sub == "worktree":
        if a[:1] == ["remove"] and ("-f" in a or "--force" in a):
            return "worktree remove --force (discards a worktree's changes)"
    return None


def check_command(command):
    """Return a reason string if the command is destructive git, else None."""
    if not command or not command.strip():
        return None
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        for pattern, label in _LEGACY:  # unbalanced quotes etc. -> never fail open
            if pattern.search(command):
                return label
        return None
    for seg in _segments(tokens):
        for idx, tok in enumerate(seg):
            if tok == "git" or tok.endswith("/git") or tok.endswith("\\git"):
                sub_i = _subcommand_index(seg, idx)
                if sub_i is None:
                    continue
                reason = _check_subcommand(seg[sub_i], seg[sub_i + 1:])
                if reason:
                    return reason
    return None


def block_message(reason):
    return (
        f"Blocked by Drydock git-safety guardrail: this command performs a {reason}. "
        "Destructive git operations require the Owner's explicit approval in chat. "
        "Explain what you want to do and why; if the Owner agrees, they run the command "
        "themselves or tell you to proceed."
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the session on malformed input
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    reason = check_command(command)
    if reason:
        print(block_message(reason), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
