# Decision Log

## Change

mutating-delegation

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | Model **A-done-right**: Codex writes directly, but in an isolated worktree with a merge-gate — not raw-A, not B | Owner's north star is throughput/endurance ("code all day"); A lets Codex self-iterate + run in parallel on its own tank, but isolation + review keep a single reviewed door onto `main` | Raw A (reject: unreviewed writes to the live branch); B — Codex proposes, Claude applies every patch (reject: Claude becomes a serial bottleneck that burns the scarce tank, and Codex can't self-test) |
| 2026-07-23 | **No auto-merge in v1** — `mutate.py` prepares + gates, the merge is a separate reviewed step | The merge onto `main` is the irreversible moment; keeping it a deliberate human/Claude action is the core safety of "A" until trust is earned | Auto-merge on green gate (reject for v1: a gate gap would land unreviewed on `main`; earn it later) |
| 2026-07-23 | **Applicability-first** gate: decide "does this apply?" before pass/fail; N/A ≠ FAIL | The Owner named the trap — a gate that fails work it doesn't apply to trains bypasses (alarm fatigue). Mirrors LaunchGuardian's applicability doctrine | A blanket "tests must pass" (reject: false-fails docs/config changes); no gate (reject: no deterministic floor) |
| 2026-07-23 | Mutating delegation is a SEPARATE `mutate.py`, NOT a `workspace-write` option on the verified read-only `delegate()` | The read-only boundary of `codex_bridge.delegate()` was adversarially verified; keeping write capability in a distinct, isolated, worktree-only function preserves that guarantee and localizes the risk | Add a `sandbox=` param to `delegate()` (reject: erodes the proven read-only lock, spreads the write surface) |
| 2026-07-23 | Cleanup removes only the temp worktree and a `codex/`-prefixed branch | A cleanup routine that could delete arbitrary branches is itself a risk; the prefix guard + worktree-path check bound the blast radius | Delete any passed branch (reject: could nuke the Owner's branch); never delete (reject: leaks branches) |
| 2026-07-23 | Codex branches from committed `base` (default HEAD), not the Owner's uncommitted WIP | A clean, reproducible starting point; the Owner's in-progress edits stay theirs and aren't shipped into Codex's context | Include the dirty working tree (reject: nondeterministic base, leaks WIP) |
