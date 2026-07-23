# Decision Log

## Change

conductor-mvp

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | v1 is **read-only only**; mutating delegation is deferred to `codex-enforcement-bridge` | Codex has no write-guard on this repo yet; a read-only conductor (review/analyze/audit) is independently valuable AND carries no repo-mutation risk, so ship the safe half now | Wait for the enforcement bridge before any conductor (rejected: needlessly blocks a safe, useful capability); allow writes now (rejected: unguarded Codex writes are the exact risk the bridge exists to close) |
| 2026-07-23 | `delegate()` **hardcodes** the safety flags (`-s read-only`, `--ephemeral`, `--skip-git-repo-check`); callers supply only prompt/schema/model/cwd | The read-only boundary must be **structural, not conventional** — no caller (or prompt-injected instruction to a caller) can escalate to writes | Pass-through flag list (rejected: a caller could inject `--dangerously-bypass-approvals-and-sandbox` or `workspace-write`) |
| 2026-07-23 | Tests use a **fake-`codex` script** invoked through the real subprocess path, not `subprocess` monkeypatching | Exercises real argv construction, stdin handling, JSONL parsing, and the `--output-last-message` file contract — with zero quota/network | Monkeypatch `subprocess.run`/`Popen` (rejected: would pass even if argv/parse logic were wrong); record-replay a real run (rejected: brittle, still needs a live capture) |
| 2026-07-23 | `discover_core()` returns the **newest** `%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`; never the `.sandbox-bin` copy | The install hash dir changes every update, and the sandbox binary is stale (can't run flagship) — discovery must track the current core | Hardcode the path (rejected: breaks on every update); an env var the user sets (rejected: fragile, undiscoverable); prefer `.sandbox-bin` (rejected: proven stale in §8) |
| 2026-07-23 | **Secret-guard** outbound: refuse to delegate content from a secret-bearing path, reusing `path_is_secret` | Delegation ships content to an external model (OpenAI); secrets must not leave the machine — the same class the plugin already guards on writes | No egress guard (rejected: silent secret exfiltration to a third party); a brand-new secret matcher (rejected: duplicates the tested `path_is_secret`) |
| 2026-07-23 | Module lives in `scripts/conductor/` (plugin-level); **not** scaffolded into user projects yet | It is orchestration tooling the plugin runs, not a per-project artifact; scaffolding + dual-copy sync is a later concern once the shape is stable | Dual-copy into `assets/project-scaffold/` now (rejected: premature, adds check_sync burden for an evolving API) — see [[drydock-dual-copy-sync]] |
