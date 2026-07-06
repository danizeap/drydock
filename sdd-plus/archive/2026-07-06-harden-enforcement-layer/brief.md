# Brief

## Change

harden-enforcement-layer

## User Need

Drydock's pitch is a deterministic safety floor: hooks that "can't be talked out of" and gates that stop unverified work from shipping. Users relying on that floor need it to actually hold — a silently bypassable guardrail is worse than none, because it buys false confidence.

## Problem

A six-dimension audit (2026-07-06, independent auditors with verified reproductions) found the enforcement layer is the leakiest tier of the product:

1. **git_safety.py is anchored-regex based and bypassable by habit, not just malice.** `git -C . reset --hard`, `git -c k=v reset --hard`, quoted flags (`git reset '--hard'`), `git checkout .` / `switch -f` / `restore --worktree .`, `+refspec` force pushes, and `clean --force` / `clean -d -f` orderings all pass. Quoted text mentioning destructive strings false-positives (confirmed against this repo's own commit messages). The block message promises a "one-time bypass" mechanism that does not exist.
2. **protect_secrets.py misses modern key types and has no Bash coverage.** `id_ed25519` (current ssh-keygen default) unprotected while `id_rsa` is; `.envrc`, keystores (`.p12/.pfx/.jks/.ppk`), and `prod.env` suffix forms missed; `.env.example` (which the scaffold's own .gitignore whitelists) is wrongly blocked; `echo KEY=x > .env` via Bash sails through — an in-session gap distinct from the documented external-process limit.
3. **hooks.json hardcodes `python3`** — on common Windows installs (python.org install + Store stub alias) the hook exits non-2 without running and Claude Code fails open: both guardrails silently inert. The one place the v0.1.4 interpreter fix missed.
4. **The packet gates are blind to their own templates.** The placeholder regex only matches whole-line `TBD`; the shipped templates use `- [ ] TBD` and `| TBD |` table cells — a 100%-pristine verification.md/decision-log.md archives cleanly (empirically confirmed). A delta spec whose `Capability:` line is missing or still the placeholder silently skips the sync gate. `requirement_present` substring-matches (false pass); the ADDED-section parser leaks into following non-Requirements sections (false block).
5. **sdd.ps1 is broken for every single-argument command** (`status`, `init`): one-element array collapses to a scalar and splatting enumerates its characters.
6. **Zero automated tests, zero CI** in a repo whose thesis is "nothing ships unverified" — the root cause of the above; and `check_sync.py` guards 1 of ~36 dual-copy pairs and is wired into nothing.

## Scope

In scope:

- `hooks/git_safety.py` — rewrite matching on a tokenized command model (shlex), close the bypass classes above, eliminate quoted-string false positives, honest block message.
- `hooks/protect_secrets.py` — pattern additions, example-file allowlist, conservative Bash write-coverage (redirection/tee/cp/mv targets).
- `hooks/hooks.json` — cross-platform interpreter invocation.
- `scripts/sdd.py` (+ scaffold copy) — placeholder gate catches template forms and Pending results; exact-name requirement matching; ADDED-section state fix; fail-closed on unparseable Capability lines; kebab validation; code-fence handling in capability parsing.
- `scripts/sdd.ps1` (+ scaffold copy) — fix argument splat; unshadow `$Args`.
- `scripts/check_sync.py` — guard all root↔scaffold pairs that must stay identical (sdd.py, sdd.ps1, CLAUDE.md, AGENTS.md, 6 templates).
- `tests/` — first test suite: hooks + gates, covering every bypass and false-positive above.
- `.github/workflows/ci.yml` — pytest + check_sync on Ubuntu/Windows, Python 3.9/3.12.
- Doc alignment for changed behavior: commands/archive.md, operator guide gate/hook sections, scaffold .gitignore secret classes, spec-delta template capability line, capabilities .gitkeep.

Out of scope (deferred to later packets):

- Skills-layer fixes (explore name collision, backend/testing contradiction, spec-sync idempotency wording, deployment routing gap).
- Sync-gate Tier 2 (MODIFIED/REMOVED/RENAMED semantic verification).
- SDD+ MCP server; any new features.
- Release/version bump (Owner decides timing).

## Acceptance Criteria

- [ ] Every audit bypass listed above is blocked, with a test proving it.
- [ ] Every confirmed false positive (quoted-string git match, .env.example block) is fixed, with a test proving it.
- [ ] A pristine packet from the shipped templates FAILS verify (placeholder gate catches checkbox/table TBD).
- [ ] `sdd.ps1 status` works.
- [ ] `check_sync.py` covers all 10 must-match pairs and passes.
- [ ] pytest suite green locally; CI workflow present.
- [ ] Independent verifier subagent review (FULL-mode gate) completed.

## Impact Areas

- Backend: hooks and CLI gate logic (Python, stdlib only).
- Frontend: none.
- Data model: none.
- API: none (CLI/hook behavior; documented in delta specs).
- AI/model behavior: none (deterministic layer only).
- Documentation: archive.md, operator guide, scaffold .gitignore, spec-delta template.
- Operations/security: this IS the security layer; gates get stricter — packets that previously passed verify with template TBDs will now be flagged (intended behavior change).

## Open Questions

- None blocking. Two judgment calls made and logged in decision-log.md: blocking remote-destructive pushes (`--delete` / `:refspec`), and limiting Bash secrets coverage to first-level writes (nested `bash -c` out of scope for v1).
