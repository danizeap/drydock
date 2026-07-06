# Tasks

## Change

release-and-update-tooling

## Implementation

- [x] Write delta spec for the release-tooling capability.
- [x] Build scripts/release.py (version lockstep, --check drift detector, preflight, print-don't-execute).
- [x] Write tests/test_release.py (temp fixtures; bump, drift, semver ordering) — 9 tests.
- [x] Fix the stale operator-guide VERSION line (0.1.3 -> 0.1.5) and add the stale-clone troubleshooting entry.
- [x] Add README "Updating" note and new docs/DEVELOPING.md (local dev-install + release process).
- [x] Add release.py --check step to CI.
- [x] Run full test suite + check_sync green; demo release.py --check catching the drift (it caught the 0.1.3 operator-guide drift live).
- [x] Independent verifier subagent review → VERIFIED (all claims held under independent execution).
