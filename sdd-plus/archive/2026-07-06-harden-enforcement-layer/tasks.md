# Tasks

## Change

harden-enforcement-layer

## Implementation

- [x] Write delta specs for git-safety-hook, secrets-protection-hook, change-packet-gates.
- [x] Build tests/ encoding every audit bypass (must-block) and false positive (must-allow).
- [x] Rewrite hooks/git_safety.py on tokenized parsing; close -C/-c/quoted/checkout./switch/restore/+refspec/clean bypasses; fix false positives; honest message.
- [x] Extend hooks/protect_secrets.py: new patterns, example-file allowlist, Bash write coverage.
- [x] Fix hooks/hooks.json interpreter invocation (python3 || python).
- [x] Fix sdd.py gates (placeholder forms, Pending result, exact requirement match, section-state leak, fail-closed capability parsing) and sync scaffold copy.
- [x] Fix sdd.ps1 single-argument splat bug (both copies).
- [x] Extend check_sync.py to all 10 must-match pairs.
- [x] Add .github/workflows/ci.yml (pytest + check_sync, ubuntu/windows × 3.9/3.12).
- [x] Align docs: archive.md gates, script-resolution rule in new/verify/archive, operator guide, scaffold .gitignore, spec-delta template, capabilities .gitkeep.
- [x] Run full test suite green; check_sync green; fill verification.md with real output.
- [x] Independent verifier subagent review (FULL gate) → VERIFIED WITH NOTES; notes resolved.
