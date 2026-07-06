# Capability: git-safety-hook

Capability: git-safety-hook

## Purpose

The destructive-git PreToolUse guard (`hooks/git_safety.py`). It reads the Bash tool-call JSON on stdin and exits 2 (block, reason on stderr) or 0 (allow). It is conservative by design: it only fires on commands that can destroy committed or uncommitted work, and it must never fail open.

## Requirements

### Requirement: Token-level command analysis
The hook SHALL analyze Bash commands as shell token sequences (not raw substrings), segmenting on shell separators (`&&`, `||`, `;`, `|`, `&`) and evaluating every `git` invocation in any segment, after skipping git global options (`-C <path>`, `-c <k=v>`, `--git-dir`, `--work-tree`, `--namespace`, `-p`, `--no-pager`, `--exec-path`, `--literal-pathspecs`) to locate the true subcommand.

#### Scenario: Global-flag prefix cannot bypass
- **WHEN** the command is `git -C . reset --hard` or `git -c core.pager=cat reset --hard`
- **THEN** the hook exits 2 naming a hard reset

#### Scenario: Quoted flags cannot bypass
- **WHEN** the command is `git reset '--hard'`
- **THEN** the hook exits 2

#### Scenario: Compound commands are inspected per segment
- **WHEN** the command is `echo done && git reset --hard`
- **THEN** the hook exits 2

#### Scenario: Quoted mentions do not false-positive
- **WHEN** the command is `git commit -m "revert the reset --hard incident"`
- **THEN** the hook exits 0

### Requirement: Working-tree-destruction coverage
The hook SHALL block the working-tree-discarding forms: `reset --hard`; `clean` with any force flag (`-f`, `--force`, combined short flags such as `-fd`/`-df`/`-fdx`); `checkout` with a `.`/`*` pathspec, with `--`, or with `-f/--force`; `switch` with `-f/--force/--discard-changes`; `restore` targeting `.` unless the restore is staged-only (`--staged` without `--worktree`); and `stash drop`/`stash clear`.

#### Scenario: checkout dot equivalent of checkout dash-dash dot
- **WHEN** the command is `git checkout .` or `git checkout -f` or `git switch -f main`
- **THEN** the hook exits 2

#### Scenario: Staged-only restore stays allowed
- **WHEN** the command is `git restore --staged .`
- **THEN** the hook exits 0

#### Scenario: Branch switching stays allowed
- **WHEN** the command is `git checkout feature-branch` or `git switch main`
- **THEN** the hook exits 0

#### Scenario: Dry-run clean stays allowed
- **WHEN** the command is `git clean -n` or `git clean -nd`
- **THEN** the hook exits 0

### Requirement: Remote-destruction coverage
The hook SHALL block force pushes in all spellings (`--force`, `-f`, a refspec beginning with `+`, `--mirror`) and remote deletions (`push --delete`, refspecs of the form `:branch`), while allowing `--force-with-lease` (bare or `=ref` form) as the sanctioned safe alternative.

#### Scenario: Plus-refspec force push blocked
- **WHEN** the command is `git push origin +main`
- **THEN** the hook exits 2

#### Scenario: Lease push allowed even alongside other flags
- **WHEN** the command is `git push --force-with-lease origin main`
- **THEN** the hook exits 0

#### Scenario: Bare force blocked even when lease also present
- **WHEN** the command is `git push --force-with-lease --force origin main`
- **THEN** the hook exits 2

### Requirement: History and ref destruction coverage
The hook SHALL block `branch -D` (and `--delete --force`), `update-ref -d`, `reflog expire` with `--expire=now` or `--expire-unreachable=now`, and `worktree remove --force`.

#### Scenario: update-ref deletion blocked
- **WHEN** the command is `git update-ref -d refs/heads/main`
- **THEN** the hook exits 2

#### Scenario: Safe branch delete allowed
- **WHEN** the command is `git branch -d merged-branch`
- **THEN** the hook exits 0

### Requirement: Fail-toward-safety parsing
WHEN a command cannot be tokenized (e.g. unbalanced quotes), the hook SHALL fall back to the legacy pattern scan rather than allowing the command unexamined, and malformed hook payloads SHALL never crash the session (exit 0 on undecodable stdin).

#### Scenario: Unbalanced quotes still guarded
- **WHEN** the command is `git reset --hard "oops` (unterminated quote)
- **THEN** the hook exits 2

### Requirement: Honest block message
The block message SHALL state the exact operation blocked and the real approval paths (Owner runs it themselves, or explicitly approves an alternative), and SHALL NOT promise bypass mechanisms that do not exist.

#### Scenario: No phantom bypass promise
- **WHEN** any command is blocked
- **THEN** the stderr message contains no reference to a per-command bypass flag or mechanism
