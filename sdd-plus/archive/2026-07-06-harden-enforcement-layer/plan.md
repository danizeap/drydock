# Plan

## Change

harden-enforcement-layer

## Approach

Test-first, in dependency order:

1. **Delta specs** for the three affected capabilities (git-safety-hook, secrets-protection-hook, change-packet-gates) — SHALL requirements with WHEN/THEN scenarios that double as the test plan.
2. **Test suite** (`tests/`): encode target behavior — every audit bypass as a must-block case, every confirmed false positive as a must-allow case, gate behavior against the actual shipped templates. Tests import the hook modules directly (hooks get small pure functions extracted; stdin/JSON `main()` preserved).
3. **Harden `git_safety.py`**: tokenize with `shlex` (posix, punctuation_chars) → segment on shell separators → for each `git` occurrence, skip git global options (`-C <p>`, `-c <kv>`, `--git-dir`, `--work-tree`, `-p/--no-pager`, ...) → per-subcommand token rules (push/reset/clean/branch/checkout/switch/restore/stash/update-ref/reflog/worktree). Tokenization kills both the quoting bypass and the quoted-string false positive. On unparseable input (unbalanced quotes), fall back to the legacy regex scan (fail toward current behavior, never open).
4. **Harden `protect_secrets.py`**: extend patterns (id_ed25519/ecdsa/dsa, .ppk/.p12/.pfx/.jks, .envrc, `*.env` suffix, service-account.json); explicit allowlist (`.env.example/.template/.sample`); new Bash coverage — parse the command for write targets (`>`/`>>` redirections, `tee`, `cp`/`mv` destinations) and block when a target matches a secret pattern.
5. **`hooks.json`**: `python3 ... || python ...` so the guard runs on python.org-Windows (where `python3` is a Store stub) and on macOS/Linux (no `python`). Both branches blocking → exit 2 either way; interpreter missing entirely → non-2 (unchanged failure mode, now far rarer).
6. **`sdd.py` gates**: broaden PLACEHOLDER to checkbox/table forms; flag `## Result` still `Pending.` in verification.md; `requirement_present` exact normalized-heading match; ADDED parser resets on any `##` heading; archive fails closed when a delta file yields no valid kebab capability; `delta_capabilities` deduped + fence-aware via the per-file helper.
7. **`sdd.ps1`**: `@()`-wrap the pipeline, rename `$Args` → `$Rest`.
8. **`check_sync.py`**: pair table (sdd.py, sdd.ps1, CLAUDE.md, AGENTS.md, 6 templates), same exit semantics.
9. **CI**: `.github/workflows/ci.yml` — pytest + check_sync, matrix {ubuntu, windows} × {3.9, 3.12}.
10. **Docs**: archive.md gate list, script-resolution rule in new/verify/archive, operator guide §4.5/§7, scaffold .gitignore secret classes, spec-delta template capability line, `.gitkeep` for scaffold capabilities dir.
11. Sync scaffold copies; run the full suite; fill verification.md with real output; independent verifier subagent review.

## Files Expected To Change

- hooks/git_safety.py, hooks/protect_secrets.py, hooks/hooks.json
- scripts/sdd.py + assets/project-scaffold/scripts/sdd.py
- scripts/sdd.ps1 + assets/project-scaffold/scripts/sdd.ps1
- scripts/check_sync.py
- tests/test_git_safety.py, tests/test_protect_secrets.py, tests/test_sdd_gates.py (new)
- .github/workflows/ci.yml (new)
- commands/archive.md, commands/new.md, commands/verify.md, docs/AI_OPERATOR_GUIDE.md
- .gitignore + assets/project-scaffold/.gitignore
- sdd-plus/templates/spec-delta.md + scaffold copy; assets/project-scaffold/sdd-plus/specs/capabilities/.gitkeep (new)
- PROJECT_CONTEXT.md (new, first-run rule), this packet

## Risks

- **Stricter gates change behavior:** packets that previously passed verify with template TBDs now warn/block. Intended, but users mid-flight will notice. Mitigation: CHANGELOG entry at release; `--force` still exists.
- **False positives from broader git rules** (e.g. blocking `checkout .`): mitigated by tokenized matching (no more substring hits), tests pinning allowed commands (`checkout <branch>`, `restore --staged .`, `push --force-with-lease`, `clean -n`), and approval-path messaging.
- **shlex edge cases:** unbalanced quotes raise; handled by legacy-regex fallback so the guard never fails open on weird input.
- **Hook double-execution** under `||` when the first interpreter blocks (exit 2 → second runs): harmless (hooks are read-only, idempotent, same verdict) — traded consciously for fail-closed cross-platform behavior.

## Rollback

Every change is in tracked text files; `git revert` of the single commit restores prior behavior. No data, no migrations, no external side effects. Hooks can be disabled instantly by removing the entry from hooks.json (Owner action).
