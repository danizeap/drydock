# Changelog

## 0.2.3 — audit-debt polish

Closes every remaining finding from the six-dimension audit; the docs now match the product. Sixth dogfooded packet.

- **README and both `CLAUDE.md` copies tell the truth about the safety layer**: five hooks, not two — including the autonomy story (self-orienting sessions with a live guardrail self-test, packet guard on ungoverned high-risk edits, "done" means verified done, every hook failing toward silence).
- **`explore` skill renamed to `explore-mode`**, breaking the duplicate `drydock:explore` registration (the skill and the command collided); the `/drydock:explore` command is unchanged and now invokes `explore-mode` — the same pattern as `spec-sync` backing `/drydock:sync`. The fix is pinned in the deterministic tier: new `tests/test_skill_command_registry.py` fails on any future skill/command id collision or skill name/directory drift.
- **Deployment/CI/infrastructure routing gap closed**: the `backend` skill now owns deployment, CI/CD pipelines, Dockerfiles, and IaC implementation (pairing with `database-steward` for migrations, `mcp-ranger` for credentials/side effects, `launchguardian` for release review), stated consistently across AGENTS.md, the operator guide, and the skill itself.
- **Skills-layer contradictions resolved**: backend now accepts justified, concretely-described manual verification (aligned with `testing`); spec-sync's stop-and-ask rule reconciled with idempotent re-runs (already-applied deltas report a no-op); `architect` and `mcp-ranger` gained the LITE/STANDARD/FULL graduation their peer skills had; one grammar fix.
- Dogfood note: the verifier's first pass returned NOT VERIFIED because the packet's own `verification.md` was still the template while tasks claimed verification done — the exact condition the completion gate exists to catch, caught by the verifier and cured before archive. Suite now 197 tests.

## 0.2.2 — packet guard

The last enforcement brick: catching ungoverned work. Fifth dogfooded packet.

- **`hooks/packet_guard.py` (PreToolUse).** When no change packet is active, edits get a risk-tiered response: **silent** for exempt/LITE work (docs, licenses, `sdd-plus/` itself, `.claude/` config, anything outside the project, or any session with an active packet); **one orientation warn per session** (allow + note: trivial edits are fine, meaningful work should open a packet) — persisted before spoken, so a state failure degrades to silence, never nagging; **deny** only for a narrow, red-team-approved high-risk list — schema migrations (`migrations/`, `db/migrate/`), **creation** of new CI configs (editing existing workflows only warns), and Dockerfiles/compose — with the recovery path in the reason. Test/fixture/example paths suppress the deny; matching is casefolded and path-aware (no string-prefix false positives); Bash write targets are covered for the deny tier so shell redirection can't dodge it.
- **Cross-hook state contract.** The red-team caught a real v0.2.1 bug: the completion gate's nudge persistence rebuilt the shared session-state dict and would have dropped foreign keys. All state writers now copy-and-update (contract documented in `_drydock_common`, pinned by a cross-hook test); `bash_write_targets` moved to the shared module so the two guards' extraction logic cannot drift.
- **Survived its own gate:** the first verifier pass returned NOT VERIFIED with three reproducible wrongful-deny classes (ancestor-directory poisoning, quoted-`>` strings, non-adjacent db+migrate) that unit fixtures structurally could not see; all three fixed, pinned by regression tests, and confirmed dead by live re-verification.
- Suite now 193 tests; stated non-goals documented in the capability spec (NotebookEdit/MCP writes → mcp-ranger's domain; Bash warn tier; per-edit packet attribution; bare quoted-`">"` tokens).

## 0.2.1 — completion integrity

Adds the Stop-hook completion gate: "done" should mean *verified* done. Third autonomy brick, shipped through Drydock's own lifecycle.

- **`hooks/completion_gate.py` (Stop hook).** When — and only when — a change packet whose implementation tasks look complete still has `verification.md` at `Pending.` AND its content changed during this session, the hook blocks the stop **once for that packet** (hard session cap) with a precise nudge: run `/drydock:verify <name>`, or explicitly tell the Owner why verification is deferred. Silent in every other case (pure conversation, work-in-progress, verification filled). **Loop-safe by construction:** the nudge ledger is persisted atomically *before* the block is spoken, so a persistence failure degrades to silence, never repetition; any error/malformed input/missing state → exit 0 (fail-toward-silence — the archive gates remain the deterministic backstop).
- **Shared `hooks/_drydock_common.py`.** Project discovery and packet fingerprinting now live in one module both hooks import, so the SessionStart stamp and the Stop gate can never drift. `session_orient.py` gains a best-effort per-session state stamp (per-user dir, hashed filename, atomic write) as the channel; it preserves the nudge ledger across auto-compaction/resume.
- **Built against a 3-adversary red-team** (loop/nag, breakage/blind-spots, state-file attacks): content-hash fingerprints (immune to git-checkout/clock-skew false nudges), completion-shaped precondition (budget can't be burned on a freshly-scaffolded packet), strict state-file schema + traversal/symlink/oversize defenses.

## 0.2.0 — autopilot floor

Moves lifecycle *orientation* and *override governance* into the deterministic tier, so the agent is self-aware of project state and the guardrails prove themselves every session — the foundation for a protocol that governs itself. Shipped through Drydock's own lifecycle (third dogfood).

- **`SessionStart` orientation hook (`hooks/session_orient.py`).** Read-only; fires every session; **silent outside a Drydock project** and **always exits 0** (it can only add context, never block or slow a session). In a Drydock project it injects state — PROJECT_CONTEXT filled/template/missing, active packets, pending tasks, unfilled verification — and a **guardrail liveness verdict** (probes `git_safety`/`protect_secrets` under this interpreter; "live" only on a genuine block + benign control + expected message; plus a static `hooks.json` wiring check). Designed against an adversarial red-team: bounded project discovery (never orients on a foreign or template repo), untrusted-`cwd` handling, `except BaseException` (SystemExit-safe), and derived-signals-only output (no file content or absolute paths).
- **Governed `--force`.** `sdd.py archive --force` now requires `--reason "<why>"` and appends an auditable override record (date, gate(s) waived, reason) to the packet's `decision-log.md`, which travels into `archive/`. Bare `--force` is refused.

## 0.1.6 — release & update tooling

Makes publishing reliable and updates discoverable, shipped through Drydock's own lifecycle (second dogfood: a verified, archived change packet with a living capability spec).

- **`scripts/release.py` — version lockstep + test-gated releases.** The version is declared in four hand-edited places (`plugin.json`, `marketplace.json`, the operator-guide `VERSION:` line, and the `CHANGELOG` heading) that kept drifting. `release.py <version>` bumps all of them together, refuses on a non-increasing version or missing CHANGELOG notes, runs the test suite + `check_sync`, and prints — never executes — the git publish commands. `release.py --check` detects drift and is wired into CI, so a version mismatch now fails the build. It immediately caught the operator guide, stale at 0.1.3 through four releases.
- **Update-path docs.** README and the operator-guide troubleshooting table now cover the most common "plugin won't update" cause — a stale per-user marketplace clone — with the one-line fix, so users can self-serve.
- **`docs/DEVELOPING.md`.** New maintainer guide: how updates actually reach users, local dev-install (run the plugin from your working tree for instant dogfooding), and the release process.
- **Tests.** `tests/test_release.py` (9 tests; suite now 126), including a negative test proving `release.py` never invokes git.

## 0.1.5 — enforcement-layer hardening (security)

Fixes every high-severity finding from an enforcement-layer audit, shipped through Drydock's own SDD+ lifecycle (its first dogfood: a `PROJECT_CONTEXT.md` plus a verified, synced, archived change packet with living capability specs).

- **Destructive-git hook, rewritten on token parsing.** `git_safety.py` now analyses commands as shell tokens instead of substrings. Closes bypasses via global flags (`git -C .`, `git -c k=v`) and quoted flags, and stops false-positiving on destructive strings quoted inside commit messages. Broadens coverage to `checkout .`/`switch -f`/`restore .` working-tree discards, `+refspec`/`--mirror`/`--delete` pushes, `update-ref -d`, `reflog expire`, and `worktree remove --force`. Honest block message (no phantom "one-time bypass").
- **Secrets hook now covers Bash writes.** `protect_secrets.py` blocks output redirections, `tee`, and `cp`/`mv` into secret paths (previously only Write/Edit), adds modern key types (`id_ed25519`), keystores (`*.p12`/`*.pfx`/`*.jks`), `.envrc`, and `service-account.json`, and stops wrongly blocking `.env.example`/`.template`/`.sample`.
- **Cross-platform hooks.** `hooks.json` invokes `python3 || python`, so the guardrails are no longer silently inert on Windows installs where `python3` is only a Store stub.
- **Deterministic packet gates.** `verify`/`archive` now catch the shipped templates' own placeholder forms (checkbox `- [ ] TBD`, `| TBD |` table cells, a still-`Pending.` Result), match requirement names exactly (no substring false-pass), respect ADDED-section boundaries, and fail closed on a delta spec with no valid `Capability:` line. Fixed the `sdd.ps1` wrapper, which was broken for single-argument commands (`status`, `init`).
- **First test suite and CI.** New `tests/` (117 tests) and GitHub Actions (Ubuntu + Windows × Python 3.9/3.12) running pytest, scaffold-parity, and live guardrail smoke-tests. `check_sync.py` now guards all 10 root↔scaffold pairs (was 1); `.gitattributes` enforces LF so the parity is stable across platforms.

## 0.1.4
- Cross-platform fix: commands and docs now invoke `python3` (with a Windows `python` note) and state an interpreter-resolution rule, instead of bare `python` which dead-ends on modern macOS where no `python` exists. README now documents the Python 3.9+ prerequisite.
- Re-saved README.md as clean UTF-8, fixing mojibake (garbled `⚓`, em-dashes, apostrophes) that showed on the GitHub and marketplace listings.
- Synced the scaffold copies of CLAUDE.md and AGENTS.md with their authoritative versions (the scaffold CLAUDE.md had been shipping stale single-hook documentation to new installs).
- Refreshed stale "0.1.1" version reference in the AI operator guide.

## 0.1.3
- Archive sync gate now checks that a delta's ADDED requirements are actually present in the living capability spec, not merely that the capability file exists. Closes a silent gap where a change could archive with an unsynced delta after the capability's first sync. ADDED requirements only; MODIFIED/REMOVED/RENAMED remain a known limitation.

## 0.1.2
- Fix stale `/sdd:sync` reference in `sdd.py` archive gate → now `/drydock:sync` (both the plugin copy and the distributed scaffold copy).
- `init` now creates `sdd-plus/specs/capabilities/`, the directory the archive gate checks against; previously every delta read as unsynced on fresh installs.
- Move the script-resolution rule out of `status.md` YAML frontmatter into the command body where it takes effect.
- Verifier subagent now checks skill blocking-rules at both the plugin-root and portability-copy paths, instead of assuming `.claude/skills/`.
- Document both PreToolUse hooks (secrets-path and git-safety) in `CLAUDE.md`; previously only secrets protection was mentioned.

## 0.1.1

- Surface the optional LaunchGuardian scanner (`pip install launchguardian`) at first touch: scanner detection in `/drydock:init-project`, a pointer in `/drydock:onboard`'s closing recap, and an availability check in the launchguardian skill before any scan commands.


## 0.1.0 — first public release

- Drydock plugin: 12 governed skills, 9 lifecycle commands, independent `verifier` subagent.
- Safety hooks: secrets-file protection (Write/Edit) and destructive-git guard (Bash).
- `/drydock:init-project` scaffolds the SDD+ project structure into any repo (never overwrites).
- `/drydock:onboard` guided first change.
- Spec lifecycle: delta specs (SHALL + WHEN/THEN) merged into living capability specs via `spec-sync`; gated archive with API blocking rule.
- LaunchGuardian Framework (22 security gates) with templates; companion scanner: `launchguardian-cli`.
- Cross-platform `sdd.py` change-packet tool with placeholder and sync gates.
