# Decision Log

## Change

release-and-update-tooling

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-06 | `release.py` prints the git commit/tag/push commands but never runs them | Publishing is the Owner's outward action (this repo commits/pushes out-of-band); the tool should prep a perfect release, not perform network/history mutations on its own. | Fully automate commit+tag+push (rejected: takes an irreversible outward action out of the Owner's hands; auth/branch assumptions); do nothing (rejected: manual release is the drift source). |
| 2026-07-06 | Treat the four version locations as one lockstep set via an explicit table | Drift comes from N independently hand-edited files; a single source that rewrites all of them (and a `--check` that fails on disagreement) removes the class. | Store version in one file and generate the others at build (rejected: no build step; plugin format needs literal versions in-place); keep hand-editing with a checklist (rejected: checklists were already implicitly in play and still drifted). |
| 2026-07-06 | `<version>` bump requires the CHANGELOG `## <version>` heading to already exist | Forces the human to write real release notes before the release goes out, rather than shipping an empty stub the tool invented. | Auto-insert a stub CHANGELOG heading (rejected: encourages empty changelogs; the notes are the one thing a human must author). |
| 2026-07-06 | Wire `release.py --check` into CI | A drift detector nobody runs is decorative — the same lesson as check_sync in v0.1.5. CI makes version drift fail the build. | Leave it as a local-only convenience (rejected: that is exactly how the operator-guide version drifted twice). |
| 2026-07-06 | `release.py` is dev-only; not added to the project scaffold or `check_sync` pairs | Releasing Drydock is a maintainer task; downstream user projects have their own release process and should not inherit Drydock's. | Ship it in the scaffold (rejected: irrelevant to consumer repos; would need its own version table). |
| 2026-07-06 | Document local dev-install as the maintainer's dogfood path | The push -> marketplace-pull -> reinstall round-trip is slow and was the direct cause of this session's stale-plugin detour. Running the plugin from the working tree makes dogfooding instant. | Keep round-tripping through GitHub (rejected: slow, and it hid a real bug for four releases). |
