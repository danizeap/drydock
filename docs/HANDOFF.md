# Drydock — handoff map

**You are looking at a working Claude Code plugin that we want to re-home onto Codex.** This file is the orientation: what the repo is, what is proven, what is guessed, and what to read in what order. It exists so you do not have to infer the architecture from 351 files.

Read this, then `docs/CODEX_PORT_PROPOSAL.md` (the proposal + the five blocking concerns Codex already raised against it).

---

## 1. What Drydock is, in one paragraph

A governance framework that makes AI-assisted development rigorous by default. It turns "vibe coding" into spec-driven development with real gates: every meaningful change opens a **change packet** (brief / plan / tasks / decision-log / verification, plus optional delta specs), gets independently verified, has its specs merged into living capability specs, and is archived. Deterministic Python enforces the parts that must not be negotiable. Version **0.12.1**, **501 passing tests**, **25 dogfooded change packets** — it was built using itself.

## 2. The one idea that matters: four enforcement tiers

Everything else follows from this. Weakest to strongest:

| Tier | What | Strength |
|---|---|---|
| 1 | **Advisory prose** — skills the agent is told to follow | probabilistic |
| 2 | **Procedural commands** — slash commands invoking defined procedures | deterministic invocation |
| 3 | **Independent verification** — a `verifier` subagent, fresh context, checks claims against reality | catches overclaims |
| 4 | **Deterministic enforcement** — hooks that block tool calls; a CLI with real exit codes | cannot be reasoned around |

Design rule: **push trust-critical outcomes to a higher tier.** Tier 4 is the reason Drydock is not just a clever prompt — and per Codex's own critique, restating that claim honestly on a new host is the single most important open question of the port.

## 3. Repo map — what's the brain vs what's the wrapping

```
scripts/sdd.py            THE LIFECYCLE. new/status/verify/triage/archive + every gate.
                          Pure Python, no harness knowledge. Ports as-is.
scripts/conductor/        The Claude→Codex bridge (see §4). NOT harness-agnostic —
                          Codex's critique corrected us on this; it is callee-specific.
scripts/brief.py          Owner-facing status engine (deterministic facts, promise ladder).
scripts/release.py        Version-bump + preflight.
scripts/check_sync.py     Guards 11 root↔scaffold file pairs from drifting.

hooks/                    TIER 4. Five hooks (secrets, git-safety, packet-guard,
                          session-orient, completion-gate) + _drydock_common.py.
                          Claude-wired today; the port's hardest question.
skills/                   12 skills (SKILL.md + blocking rules). Same format Codex uses.
commands/                 13 slash commands. Codex has no commands dir → fold into skills.
agents/verifier.md        The tier-3 verifier subagent.

sdd-plus/
  specs/capabilities/     LIVING SPECS — the durable source of truth.
  changes/                Active packets. (Currently empty: nothing in flight.)
  archive/                25 completed packets — the evidence trail. Worth skimming
                          two or three; they show the process actually working.
  standards/ protocols/   How work should be done.

assets/project-scaffold/  What gets written into a user's project on init,
                          including .codex/hooks/drydock_guard.py (the existing
                          Codex-side guard bridge).
tests/                    501 tests. The behavioral contract.
docs/                     AI_OPERATOR_GUIDE.md is the authoritative reference.
```

## 4. The conductor — Claude already drives Codex

This is the part most relevant to the port, because the direction is about to invert. All of it is live-proven on the owner's machine:

- **`codex_bridge.py`** — discovers the Codex core binary, reads rate limits via `app-server`, routes a model by remaining fuel, delegates with hardcoded `-s read-only --ephemeral` flags and a fail-closed secret guard.
- **`review.py`** — `--diff` sends the *current content* of changed files for a schema-locked review. (Whole files, not hunks — deliberately; a field report proved hunks miss whole classes of finding.)
- **`mutate.py`** — Codex writes code in an **isolated git worktree** on a `codex/…` branch, never the owner's branch. The diff passes an applicability-first gate. **Never auto-merges.**
- **`negotiate.py`** — two-brain plan negotiation, bounded by a round cap. **This file critiqued the port proposal you are about to read.**
- **`coord.py`** — TTL-cached, single-flight fuel gauge shared across concurrent sessions.

## 5. What is proven vs what is assumed

Stated plainly so nothing gets built on a guess:

**Proven on the owner's machine**
- The whole Claude-side lifecycle (501 tests, 25 archived packets).
- Claude→Codex delegation: review, mutate-in-worktree, plan negotiation.
- Codex hook payloads are Claude-compatible (the `.codex/` guard bridge works for the secrets + destructive-git floor).
- Codex has a real plugin + marketplace system that accepts third-party Git sources.
- Cross-model review catches **disjoint** defect classes — measured, near-zero overlap.
- Claude Code has a full headless interface (`claude -p --output-format json`, model/permission/tool flags).

**NOT proven — treat as open**
- The authenticated Codex→Claude round trip. Our test returned `Not logged in` because this agent runs in a managed session whose on-disk credential file is empty. Needs one 10-second check from a normal terminal.
- Whether all five hooks port to Codex. The existing bridge covers only the stateless floor, **fails open**, and the originals key on Claude tool names (`Write`, `Edit`) vs Codex's canonical ones (`apply_patch`, `Bash`).
- Whether plugin-bundled hooks can carry a tier-4 claim. Codex says they can be bundled but are *non-managed*: hash-trusted, user-disableable, not covering every tool path.
- How execution subagents should work under a Codex host.

## 6. Reading order

1. **`docs/CODEX_PORT_PROPOSAL.md`** — the proposal, and the five blocking concerns Codex raised against it. Start here; it is a conversation already in progress.
2. **`docs/AI_OPERATOR_GUIDE.md`** — the authoritative behavior reference. Written for an AI reader.
3. **`scripts/sdd.py`** — read `archive_readiness`, `cmd_verify`, `cmd_archive`, `cmd_abandon`. That is the lifecycle's spine.
4. **`hooks/`** + `assets/project-scaffold/.codex/hooks/drydock_guard.py` — the tier-4 story and its existing Codex bridge.
5. **`scripts/conductor/`** — the bridge that is about to invert.
6. Two archived packets, e.g. `sdd-plus/archive/2026-07-24-honest-finish/` and `…-codex-coplan/` — to see a full packet lifecycle and what "verified" means in practice.
7. `CHANGELOG.md` — the last five entries carry the design reasoning.

## 7. House rules that shaped everything

Worth knowing, because they explain choices that would otherwise look paranoid:

- **Never report an absence of evidence as a positive result.** A cost meter that reads `0` because it lacks resolution is a lie. An unmeasured repetition is `unknown`, not "repetitive". This bug shipped three times in one week before it was named.
- **Never claim more than the mechanism backs.** A comment saying "genuinely empty" over code that only checks uncommitted changes is how future data loss ships.
- **A regression test must be proven to fail against the defect it guards.** One did not, and was rewritten.
- **A verifier needs a frozen tree.** A verdict on a moving target reads authoritative and describes nothing.
- **`--force` waives a gate on work you stand behind; `--abandon` buries work you do not.** Neither ever fabricates a PASS.

## 8. Current state

- Working tree clean, nothing in flight (`sdd-plus/changes/` empty).
- `python -m pytest -q` → 501 passed, 6 skipped. `python scripts/check_sync.py` → 11/11.
- Claude marketplace: `danizeap/drydock`.
- Requires Python 3.9+ and git. Developed on Windows; the CLI is cross-platform.
