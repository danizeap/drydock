# Decision Log

## Change

harden-enforcement-layer

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-06 | Tokenize commands (shlex) instead of adding more regexes to git_safety | Anchored regexes are the root cause of both bypass classes (global flags, quoting) AND the false positives (quoted mentions). One structural fix closes all three. | More regex variants (rejected: whack-a-mole, keeps false positives); calling `git` to parse (rejected: hook must be dependency-free and side-effect-free). |
| 2026-07-06 | On unparseable input, fall back to legacy regex scan | Guard must never fail open; unbalanced quotes are rare and legacy behavior is the known floor. | Fail closed on parse error (rejected: blocks legitimate complex commands too aggressively); allow on parse error (rejected: trivial bypass via deliberate bad quoting). |
| 2026-07-06 | Block remote-destructive pushes: `push --delete`, `push :refspec`, `push --mirror` | Deletes work on the remote — same "destroys committed work" class as force-push; Owner approval path exists for legitimate cleanup. | Allow (rejected: remote deletion is harder to recover than local); warn-only (hooks have no warn channel — exit is binary). |
| 2026-07-06 | Keep `--force-with-lease` allowed, including when spelled `--force-with-lease=ref` | Lease pushes are the sanctioned safe alternative; token-level matching now distinguishes them from bare `--force` reliably. | Blocking all force variants (rejected: removes the recommended safe path). |
| 2026-07-06 | Allow `.env.example` / `.env.template` / `.env.sample` in protect_secrets | The scaffold's own .gitignore whitelists `!.env.example`; example files are documentation, not secrets. Contradiction confirmed by audit. | Keep blocking (rejected: hook fights the project's own conventions). |
| 2026-07-06 | Bash secrets coverage: first-level write targets only (`>`, `>>`, `tee`, `cp`, `mv`) | Covers the demonstrated gap (`echo KEY=x > .env`) with near-zero false-positive risk. Nested `bash -c "..."` strings are a documented v1 limitation. | Full shell AST parsing (rejected: complexity/fragility in a stdlib-only hook); no Bash coverage (rejected: confirmed in-session gap). |
| 2026-07-06 | hooks.json uses `python3 "..." || python "..."` | Fail-closed on python.org-Windows (python3 = Store stub, exits non-zero, fallback runs) and on macOS/Linux (no `python`). `||` works in both cmd and POSIX sh. Double-run when first blocks is harmless (read-only, idempotent). | Single interpreter (rejected: silently inert guardrails on one platform — the audit's top finding); shipping a launcher script (rejected: more moving parts for the same result). |
| 2026-07-06 | Placeholder gate flags any structural TBD line + `## Result` still `Pending.` | The gate existed to stop template-residue archives; it must at minimum catch the templates Drydock itself ships (`- [ ] TBD`, `| TBD | ... |`). Empirically it caught neither. | Flag any TBD substring anywhere (rejected: false-positives prose discussing TBDs); leave as-is (rejected: gate is provably decorative). |
| 2026-07-06 | Archive fails closed when a delta spec yields no valid kebab capability | A delta the gate cannot attribute is a delta the gate cannot check; silently skipping it re-opens the unsynced-delta hole 0.1.3 closed. `--force` remains the explicit override. | Warn and continue (rejected: silent false-pass is the exact bug class this repo keeps re-finding). |
| 2026-07-06 | Tests import hook modules and call pure functions; `main()` stays stdin/JSON | Fast, interpreter-independent tests; hooks stay single-file and stdlib-only. | Subprocess-based tests (kept for two end-to-end smoke cases only; rejected as the main strategy: slow, interpreter-path fragile on Windows). |
| 2026-07-06 | check_sync.py grows a pair table (10 pairs) instead of per-file scripts | One guard, one exit code, wired into CI; kills the drift class that has recurred three times this session. | Guarding only sdd.py (rejected: CLAUDE.md drift already shipped stale hook docs to new installs once). |
