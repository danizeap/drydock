# Brief

## Change

codex-mutate-scope

## User Need

Field report §6.3, from a real build day: a **one-tool change ingested 553,941 tokens**. The north star is delegating all day across resets — a delegation that silently eats a large fraction of a tank is a fuel leak, and right now there is no gauge on it. The Owner cannot see what a run cost until the tank is visibly lower.

## Problem

Three distinct problems, only the first of which is what the report named:

1. **The cost is invisible.** `delegate_mutation` already captures Codex's `usage` from `turn.completed` and throws it away — `mutate()` never surfaces it, and never compares the fuel gauge before and after. We built a fuel gauge and then put the single most expensive operation behind it with no meter.
2. **There is no way to bound what Codex reads.** The worktree is a full checkout because the test gate needs a runnable tree, so Codex crawls to find its targets. `review.py` solved the same problem by sending exactly the files — but that solution does not transfer, because review never has to *run* anything.
3. **The gate is silently weakest exactly where review matters most.** The reporter's own judgment: a dozen files of non-repetitive, judgment-heavy work is the case to *avoid* delegating, because "tests pass" means least there and the review burden is highest. Nothing in the tool says so. Review is the load-bearing safety step, and a wide unfamiliar diff quietly erodes it.

The reporter's usage is **bimodal**, which is what makes scoping a flag rather than a default:

- **Small and coupled (1–5 files)** — "add a tool like the existing one." Their actual run was 3 files: the tool body, the test's expected-tools list, and the i18n labels. One logical change fanning across coupled files. Highest frequency; scoping is a clear win.
- **Wide and mechanical (12+)** — rename a symbol, add a parameter to every call site. Whole-repo context is arguably *correct* here; scoping would hurt.

## Scope

In scope:

- **Cost metering**: normalized token usage + authoritative fuel delta (gauge before/after) on every mutating run, reported whether the run succeeds or fails.
- **`--files` — opt-in, SOFT scoping**: named targets are inlined into the prompt (so Codex does not have to crawl to find them) and Codex is told to start there; it may still edit outside, and any out-of-scope edit is **disclosed**, never silently allowed or silently blocked.
- **Secret guard on inlined content**: naming a file for inlining sends its content off-machine, so it gets the same by-name and by-content refusal `review.py` applies to explicitly named paths.
- **Diff-shape advisory**: report diff width and cross-file repetition, and when a diff is wide *and* divergent, say plainly that the test gate is weak evidence for it. Advisory only — it never gates.

Out of scope:

- **Hard scoping / sparse checkout.** Physically removing files from the worktree is real enforcement, but the test gate needs a runnable tree — a partial checkout makes tests fail for reasons unrelated to the code, which is the N/A-vs-FAIL trap already fixed once. Revisit only if metering proves prompt-side scoping insufficient.
- **Tool-derived scope for the sweep case** (e.g. `git grep` to compute a rename's call sites). Promising — the tool could compute a better file set than Codex finds by crawling — but it depends on whether Codex behaves better when handed a list than when told to search. Metering answers that first.
- Any change to merge behavior. This module still never merges.

## Acceptance Criteria

- [ ] Every mutating run reports what it cost — tokens where Codex provides them, and the fuel-gauge delta as the authoritative figure.
- [ ] An unreadable or failed measurement reports `null`, never a fabricated number.
- [ ] `--files` is opt-in; omitting it leaves today's behavior byte-for-byte unchanged.
- [ ] A named file that is secret-bearing by name or by content is **refused** — its content is never inlined.
- [ ] Codex editing outside the declared scope is reported in the result, not swallowed and not blocked.
- [ ] A wide, divergent diff raises an advisory naming the review burden; a wide, repetitive one does not.
- [ ] The advisory never changes `clears` — the gate verdict is untouched.

## Impact Areas

- Backend: `scripts/conductor/mutate.py` only.
- Frontend: none.
- Data model: none.
- API: `mutate()` gains `files=` ; result gains `cost`, `scope`, `diff_shape`.
- AI/model behavior: the delegation prompt gains an inlined-targets preamble when `--files` is used.
- Documentation: operator guide's mutating-delegation paragraph.
- Operations/security: file content is inlined into a prompt — same egress risk as `review.py`, so the same guard.

## Open Questions

- What repetition threshold actually separates "mechanical sweep" from "judgment-heavy"? Provisional values are set from reasoning, not data. **Stop condition: they must be advisory-only until calibrated against real diffs.**
- Does Codex genuinely read less when handed inlined targets, or does it crawl anyway? Metering is what will answer this — the honest position today is that `--files` is expected to help and unproven.
