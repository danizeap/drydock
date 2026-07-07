# Plan

## Change

owner-brief

## Approach

Build in dependency order, red-team findings folded in before code:

1. **Ledger primitive** (`hooks/_drydock_common.py`): `append_event(root, hook, action, category)` writing one NDJSON line `{ts, hook, action, category}` to `<state_dir>/journal-<sha256(root)[:16]>.ndjson`. O_APPEND single-line writes; size cap with truncate-and-restart rotation; category-only vocabulary (fixed set — never paths, commands, or content); `except BaseException: return` so an append can never alter a caller's behavior. A reader `read_events(root)` with the same strictness discipline as `read_state` (size cap, per-line JSON validation, skip-don't-crash on bad lines).
2. **Wire the four writers**: packet_guard (deny → `packet-deny:<class>`, warn → `packet-warn`), protect_secrets (deny → `secrets-deny`), git_safety (deny → `git-deny`), completion_gate (nudge → `verify-nudge`). Each call sits strictly after the verdict is decided and is individually wrapped; polarity unchanged (secrets/git keep failing toward blocking, gate toward silence).
3. **FACTS engine** (`scripts/brief.py`, plugin-only): stdlib-only; `sys.path` shim to import `_drydock_common`. Reads: active packets (tasks/verification state via existing fingerprint parsing), archive dirs (date + name + brief first-paragraph/Owner-line + verification Result), ledger events (category counts, last-N), PROJECT_CONTEXT presence, OWNER_STATUS fingerprint. Emits a fenced JSON FACTS block: per-item promise-ladder rung assigned by code (brief-only → idea; pending tasks → being built; tasks done + verification Pending → built-not-yet-checked; Result PASS → independently checked; archived → done & documented), provenance class per claim, `"unavailable"` markers wherever a source cannot be read, generated-at date + project fingerprint. Exit 0 with a valid block even on partial failure; a crash is visible (commands are retryable, unlike hooks).
4. **Command** (`commands/brief.md`): run the engine; render ONLY the FACTS block in the Owner's language (translate, never add; absence stays absence; every item ends "nothing needed" or "your move: <one decision>"; ladder captions "what you can safely say"); then write OWNER_STATUS.md (header: generated date + "snapshot — ask for a fresh brief"; HTML-comment fingerprint) as an explicit visible step.
5. **Sentinel** (`hooks/session_orient.py`): read OWNER_STATUS.md (size-capped), extract embedded fingerprint, compare to freshly computed; on mismatch append one line to the existing capped context. Read-only; all errors silent.
6. **Prose wiring**: `commands/new.md` — fill the brief template's Owner line; `commands/archive.md` — closing offer of a brief refresh.
7. **Tests + docs**: unit tests for append/read/rotation/corruption/verdict-independence; brief.py golden-output tests against synthetic project trees (each ladder rung, unavailable ledger, stale fingerprint); sentinel tests; wiring smoke in CI. Operator guide + README.

Red-team first (3 adversaries: false-peace/lying-brief, ledger robustness/privacy/latency, adoption/nag), then implement against findings. Verifier subagent before archive; sync deltas; release 0.3.0 Owner-gated.

## Red-team response (2026-07-07 — 22 attacks, 2 critical live-confirmed; all mitigations adopted)

**Trust chain (lying-brief adversary):**
1. *Verification laundering (CRITICAL, live-confirmed: forged one-line "PASS." passes both parsers; a NOT VERIFIED Result also reads as "filled")* — brief.py gets its OWN rung assigner, never reusing the completion gate's fail-toward-silence parsers. Ascent requires positive evidence: idea unless tasks.md has ≥1 checkbox; built-not-yet-checked requires ≥1 checked AND 0 pending; the checked rung requires a `## Result` section whose first content matches a closed PASS grammar (PASS / PASS WITH OPEN QUESTIONS); NOT VERIFIED / BLOCKED / FAIL / headingless / unparseable freeze at built-not-yet-checked with "record present but not a pass". The word "independently" never renders from typeable state — the rung is "checked & recorded". Provenance caption upgrades to "confirmed on this computer" only when a `verify-run` ledger event (packet name + content-hash, written by `brief.py --record-verify <name>` which re-runs the deterministic gate itself and appends only on genuine pass; invoked by commands/verify.md after the gate) matches the packet's CURRENT hash — post-verification edits demote the caption automatically. Per-machine gap degrades the caption, never the rung.
2. *Model-authored, write-unguarded status file (CRITICAL)* — brief.py `--write-status` renders OWNER_STATUS.md ITSELF from the FACTS block via frozen per-language label sets (deterministic bytes; golden-tested); the model's language latitude applies to the ephemeral chat rendering only. packet_guard gains an always-deny class for basename `owner_status.md` (Write/Edit/MultiEdit + Bash write targets; fires even with an active packet; recovery message: "generated file — run /drydock:brief"; test/fixture suppression retained). Freelance green files become impossible without disabling the guard.
3. *--force archive laundering* — the engine parses each archive dir's decision-log for `## Override` and verification Result with the affirmative grammar: waived gates or non-PASS caps at "archived with recorded exceptions: <gates>" + your-move; artifact-incomplete (hand-moved) archive dirs render "archive record incomplete", no rung.
4. *Probe pollution* — session_orient's `_run_guard` sets `DRYDOCK_PROBE=1` in the child env; append_event no-ops under it (verdict paths never read it). Tests: a full orientation pass leaves the ledger byte-identical; the env var cannot fail a guard open; a real deny between probes counts exactly once.
5. *Aspirational Owner-line* — FACTS field is named `goal` (one deterministic sentence-truncation); status templates prefix it ("Goal:") below the top rung; commands/new.md pins a two-slot form ("After X, you can Y"); verify checklist gains an Owner-line concreteness check.
6. *Per-machine blind spots* — append_event writes `ledger-created` on first creation; session_orient appends one `session` marker per startup; counts always render bounded ("on this computer, across N sessions since <date>"); archive dates predating ledger birth force a "history from other computers or earlier dates is not visible here" marker.
7. *GitHub staleness* — visible first line: "Snapshot generated <date> — anything after this date is not reflected"; git HEAD short-sha embedded via stdlib read of .git/HEAD ("as of commit abc1234", else "commit: unavailable"); top-rung captions carry "as of <date>"; commands/archive.md's closing step regenerates the file (reported, not silent) when one exists.

**Ledger & guard paths (robustness adversary):**
8. *Latency/fail-open at the timeout tail* — NEVER fsync (the ledger is a disposable cache); append is the last statement after the verdict is fully written to stdout/stderr; appends fire only on non-silent verdicts (allow path adds zero I/O; existing latency test preserved). New verdict-DELIVERY test: slow/unwritable state dir ⇒ exit code + stdout + stderr byte-identical for all four writers.
9. *Import hijack / version skew* — brief.py resolves the hooks dir strictly from `Path(__file__).resolve().parent.parent / "hooks"`, inserted at sys.path[0]; never cwd, never env. Test plants decoy `_drydock_common.py` in cwd and a fake project root and asserts the plugin module wins.
10. *Reader poisoning* — read_events mirrors read_state's lstat + S_ISREG discipline (O_NOFOLLOW where available), reads only a bounded tail window, enforces per-line max length, decodes errors='replace', json-parses per line skipping bad lines. Writer opens O_APPEND|O_CREAT (|O_NOFOLLOW) after an lstat check. Tests: symlinked journal, oversized line, non-UTF8 bytes, torn half-lines.
11. *Category/timestamp leaks* — append_event validates category against a FROZEN allowlist at the sink (non-members coerce to "other", never written verbatim; path-bearing test pinned); `ts` is date-only; rendering uses counts and coarse ranges, never raw timestamps.
12. *Stale path-hash reuse* — read-side bound: events dated before the project's earliest observable signal (oldest archive date) are ignored; per-path-per-machine semantics documented in the capability spec.
13. *State-dir env divergence* — read_events probes the full candidate-base list for a matching journal file (write side unchanged); operator guide documents the diagnostic.
14. *Concurrency/rotation* — one complete line per single os.write to an O_APPEND fd; stat-before-open size check; over-cap triggers opportunistic os.replace rotation, all swallowed; the reader's tail window is the true growth bound.

**Adoption (nag adversary):**
15. *Chronic-yellow sentinel* — reworded from an offer-generator to a trust instruction ("do not cite OWNER_STATUS.md as current; if the Owner asks about status, run /drydock:brief"), emitted only for source in (startup, clear) — resume/compaction never re-arm it; commands/brief.md pins: never run unprompted.
16. *Counts drama* — windowed counts ("since <date>") + the pinned honest-cost sentence ("pauses are recoverable; occasionally a pause is a false alarm, which costs a retry, not lost work").
17. *Git churn vs GitHub visibility* — the first write ends with one explicit Owner choice: commit (visible, lags — header shows the date) or .gitignore (private to this machine); no-change short-circuit (fingerprint match ⇒ "status unchanged since <date>", no rewrite — deterministic authorship makes byte-stable output true by construction).
18. *Not-initialized repo* — engine emits a distinguished `{"drydock": "not-initialized"}` FACTS block, exit 0; the command says one sentence pointing at /drydock:init-project and does NOT write the file. Golden test.
19. *Language fork* — the fingerprint comment records `lang=<code>`; regeneration reuses it unless the Owner asks to switch; frozen label sets ship en + es (file layer); chat rendering remains any-language; the sentinel line stays English but instructs offering the refresh in the Owner's language.
20. *Three-surfaces confusion* — authority order written into commands/status.md ("engineering view — offer /drydock:brief for product terms"), commands/brief.md ("live state wins; the snapshot is stale; never reconcile by hand"), and the operator guide inventory.

## Files Expected To Change

- `hooks/_drydock_common.py` (append_event, read_events, category vocabulary)
- `hooks/packet_guard.py`, `hooks/protect_secrets.py`, `hooks/git_safety.py`, `hooks/completion_gate.py` (append calls)
- `hooks/session_orient.py` (staleness sentinel)
- `scripts/brief.py` (new, plugin-only)
- `commands/brief.md` (new), `commands/new.md`, `commands/archive.md`
- `tests/test_event_ledger.py`, `tests/test_brief.py` (new), touches to existing hook tests
- `docs/AI_OPERATOR_GUIDE.md`, `README.md`, `.github/workflows/ci.yml` (smoke), `CHANGELOG.md` (at release)
- Delta specs: `specs/owner-brief.md` (new capability), `specs/session-orientation.md` (sentinel requirement)

## Risks

- **A lying brief** — the design's death condition. Mitigations are structural: states assigned only by code; translate-only command rules; absence-as-absence pinned in spec + tests; embedded fingerprint + sentinel bound staleness to one session.
- **Guard-path regression**: an append bug changing a verdict or adding latency. Mitigations: append strictly post-verdict, per-call swallow-all, verdict-independence tests (append target unwritable → verdict identical), latency budget test reuse.
- **Ledger growth/concurrency**: two sessions appending; unbounded file. Mitigations: O_APPEND one-line writes, size cap + rotation, reader skips bad lines.
- **Privacy**: events must stay category-only; test asserts no path/command content in written lines.
- **Version skew**: older scaffolded projects lack the Owner line — engine falls back to User Need first paragraph; no sdd.py changes at all in this packet.
- **CRLF/Windows**: OWNER_STATUS written utf-8 `\n` via mkstemp+replace; file is Owner-committed knowingly (command output says it was written).

## Rollback

Every piece is additive and independently disableable: remove the four append calls (guards return to v0.2.3 behavior); delete brief.py + commands/brief.md (command disappears); revert the sentinel block in session_orient. No data migration — the ledger is a per-user cache file that can be deleted freely. OWNER_STATUS.md is a generated snapshot; deleting it loses nothing.
