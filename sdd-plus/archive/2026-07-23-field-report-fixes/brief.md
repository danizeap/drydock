# Brief

## Change

field-report-fixes — act on the first real-world field report (Drydock 0.8.0, a live Next.js/Supabase build day). Closes a **dangerous false-GREEN in the mutating-delegation gate** plus four smaller correctness/ergonomics defects the operator hit in anger.

Intake: Mode STANDARD, but the headline item is safety-critical (a review gate reporting green when it could not verify) so it gets a `verifier` pass. Primary skill: `backend`. Approvals: Owner supplied the field report and directed holding the release until the feedback is folded in. Stop conditions: any path where the gate reports green on a result whose *top-level command shape* it could not verify. (Masking inside a delegated script — `npm run ci`, `bash -c "…"` — is outside what a top-level scan can reach; it is a declared, disclosed limit, not a stop condition.)

## What this means for your product

The merge gate stops reporting green on results it cannot actually verify. It now trusts a test command **only** when the command is simple (optionally `&&`-chained, the one form where a failure propagates); a pipe, `;`/`&` sequencing, `||`, a newline or a subshell all make the exit code untrustworthy, and a Node worktree with no installed deps makes the run meaningless. In those cases the verdict is **`unverifiable`, `clears: false`** — never a confident green. It also flags "you added code but no test" as an advisory, and the handoff snapshot stops drowning you in finished packets.

Honest scope: this closes the *exit-code-trust* class via an allow-list (unrecognised constructs are untrusted by default). It does not make a passing test *correct* — only a green you can believe.

## User Need

A real operator ran a mutating delegation with `--test-cmd "npx vitest run … | tail -6"`. The gate read `tail`'s exit code (0) and reported **`green, clears: true, "code changed; tests pass"`** — for tests that may never have meaningfully run. A false green on a review gate fails in the *dangerous* direction: it invites a merge the gate was supposed to guard. Reproduced verbatim before fixing.

## Scope

In scope (from the field report):
- **6.1 [HIGH]** shell-masked exit code → new `unverifiable` verdict, `clears: false`. Trust is an **allow-list**: simple command, optionally `&&`-chained. Pipe, `;`, bare `&`, `||`, newline, backtick, `$( )` → untrusted; unrecognised constructs untrusted by default; trust signal defaults to false (fail-closed); quoting is platform-aware (cmd.exe does not quote with `'`).
- **6.2 [MED]** worktree has `package.json` but no `node_modules` → tests can't resolve deps → also `unverifiable`, never green.
- **6.4 [MED]** coverage-gap **advisory** (new/changed code with no test file in the diff) — informational, not a hard fail.
- **6.5 [LOW]** handoff listed every un-archived packet as "active" (48 on the reporter's box) → now reports `packets` (all) + `in_flight_packets` (unchecked tasks / unfilled verification).
- **6.6 [LOW]** handoff `write` now emits `path` (what callers expect) alongside `wrote`.
- **6.7 [LOW]** review findings gain a required `file` field so multi-file reviews are triageable.

Out of scope (next packet): 6.3 (mutate context scoping / `--files` hint) and the §7 features — `codex-review --diff`, cross-model review as a rung in `verify`, the verification-ladder record, fleet fuel in the brief.

## Acceptance Criteria

- [ ] A piped `--test-cmd` can NEVER produce `green`/`clears: true` (reproduced before, fixed after).
- [ ] A worktree missing installed deps can never produce a green.
- [ ] Honest passes still go green; honest failures still go red (no over-blocking).
- [ ] Coverage-gap advisory fires on code-without-tests and is silent otherwise.
- [ ] Handoff distinguishes all packets from in-flight; `write` emits `path`.
- [ ] Full suite green; no regressions.

## Impact Areas

- Backend: `mutate.py` (gate + test-result trust), `handoff.py` (packet reporting + result payload), `review.py`/`review_schema.json` (per-finding `file`).
- API: new gate verdict `unverifiable`; gate result gains `advisories`; handoff state keys renamed (`packets`/`in_flight_packets`).
- Operations/security: closes a gate that failed in the unsafe direction.
- Documentation: delta spec; the field report's triangulation story is worth surfacing in docs (deferred to the docs pass).

## Open Questions

- Should `unverifiable` eventually be surfaced differently from `blocked` in any future auto-merge policy? (Both are `clears: false` today, which is the safe answer.)
