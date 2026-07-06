# Verification

## Change

harden-enforcement-layer

## Automated Checks

- [x] `python -m pytest tests/ -q` → **117 passed** (test_git_safety 58, test_protect_secrets 40, test_sdd_gates 19). Encodes every audit bypass as a must-block case and every confirmed false positive as a must-allow case. (Count grew from 113 → 117 after two dogfood-found placeholder false positives were fixed with added regression tests.)
- [x] `python scripts/check_sync.py` → **OK: all 10 root/scaffold pairs are identical** (exit 0). Now guards sdd.py, sdd.ps1, CLAUDE.md, AGENTS.md, and the 6 templates (was 1 of ~36).
- [x] `python -c "import ast; ast.parse(open('scripts/sdd.py').read())"` → parses OK; scaffold copy byte-identical (`cmp`).
- [x] End-to-end hook `main()` via real stdin: `git reset --hard` → exit 2; `git -C . reset --hard` (the bypass) → exit 2; `git status` → exit 0; `git commit -m "...reset --hard..."` (false positive) → exit 0; `Write .env` → exit 2; `echo K=v > .env` (Bash) → exit 2.

## Manual Checks

- [x] `powershell -File scripts/sdd.ps1 status` → prints the packet status (previously errored `invalid choice: 's'`).
- [x] Reworded spec-delta template capability line still parses to `[]` (fail-closed placeholder), confirmed against the shipped template.
- [x] The active installed plugin hook (old version) blocked a Bash command merely *mentioning* `git reset --hard` — a live reproduction of the false-positive bug this change fixes; the new working-tree hook allows the same command.
- [x] CI smoke-block logic simulated locally: all four blocking payloads exit 2, `git status` exits 0.

## Documentation Updates

- [x] README or user-facing docs updated: operator guide §1.1/§4.5/§7 (hook + archive-gate behavior) rewritten to match; commands/archive.md gate 5 + script-resolution rule; new.md/verify.md resolution rule.
- [x] Project context updated: `PROJECT_CONTEXT.md` created (first-run rule finally satisfied).
- [x] Specs updated: 3 delta specs added (git-safety-hook, secrets-protection-hook, change-packet-gates). NOTE: not yet synced into living capability specs — that is the `/drydock:sync` step before archive.
- [ ] No documentation update needed. Reason: (n/a — docs were updated)

## Independent Verification

- [x] `drydock:verifier` subagent review (FULL-mode gate) → **VERIFIED WITH NOTES** (2026-07-06). Independently re-ran pytest (117 passed), check_sync (10/10, exit 0), and ast parse; mapped all 13 delta-spec requirements to asserting tests (all IMPLEMENTED with file:line); drove 19 adversarial payloads through the new hooks confirming every audit bypass blocks and every false positive allows; found no secrets in the diff and no scope creep. Two non-blocking notes (stale "113" count — now corrected here; `.gitignore` + EOL-normalized templates under-listed in the scope line — both confirmed benign) resolved.

## Result

**PASS.** Implementation complete and independently verified. 117 tests green, check_sync green (10 pairs), all hook behaviors confirmed end-to-end by the verifier, sdd.ps1 fixed, packet passes its own placeholder gate. Remaining before archive (Owner-gated): (1) `/drydock:sync` to merge the 3 delta specs into living capability specs, (2) Owner decision on commit / v0.1.5 release.
