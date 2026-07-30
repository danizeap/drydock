# Verification

## Change

peer-unavailable-governance

## Automated Checks

- [x] Focused orchestrator suite: `31 passed`.
- [x] Codex adapter suite after final fallback coverage:
  `122 passed, 2 skipped`.
- [x] Legacy suite: `548 passed, 6 skipped`.
- [x] Root/scaffold parity: all 11 pairs identical.
- [x] Project-scaffold bundle matches source.
- [x] Hook runtime and trusted definition match source.
- [x] Release version parity: all locations agree at `0.12.1`.
- [x] `git diff --check` reported no whitespace errors.
- [x] Packet structure verification completed at the implementation
  checkpoint; Codex-only dogfood and separate review were still pending then.

## Manual Checks

- [x] Reviewed every operational stage admitted to `single_pilot`.
- [x] Reviewed every contract/control stage retained as `return_to_owner`.
- [x] Confirmed raw peer result text and stderr are not returned by the new
  rate-limit classification result.
- [x] Confirmed Windows timeout uses a kill-on-close Job Object and no
  `taskkill` lookup.
- [x] Confirmed POSIX containment is described as best effort.
- [x] Confirmed timeout cleanup and output drain are bounded and documented
  outside the requested peer deadline.
- [x] No live Claude model call, credential read, or usage endpoint call was
  made.
- [x] A separate read-only Codex verifier returned `PASS` for the exact
  executable candidate. It reported `epistemic_independence: false`; this is
  not cross-model agreement.

## Documentation Updates

- [x] Shipped Codex orchestration skill updated.
- [x] AI operator guide updated.
- [x] Delta spec added.
- [x] Project context did not require an update.

## Result

PASS for the packet implementation and the Codex-only dogfood recorded below.
The separate verifier passed the exact executable candidate. Peer convergence
remains `not_established`, and same-model process isolation is not epistemic
independence. No push, release, sync, or archive is authorized by this result.

## 2026-07-30 Codex-only dogfood preflight

- Workflow objective: `153b5868399719d907cc2156ec5c5fdd`.
- The stored phase subsequence omitted `plan_peer` and `cross_review` and
  advanced from preflight directly to mutation.
- Mutation admission
  `2a54b1a2df439b52e0dfcc65af08d1c25944deef2143a7f408d2326aeee08f91`
  was issued but remained unconsumed.
- The runner stopped before worktree creation, worker spawn, or provider usage:
  Git 2.54 returned exit 128 for an absent `.git/config.worktree` while
  `extensions.worktreeConfig=true`.
- No Claude or Codex model call occurred, no candidate exists, and no workflow
  gate passed from this attempt.
- The workflow and admission are not reusable after the runner mechanism is
  corrected.
- The corrected preflight parses the exact common config file without
  implicitly loading per-worktree configuration, treats the optional file as
  empty when absent, and type-checks and parses it directly when present.
- Focused Git-config regressions: `3 passed, 76 deselected`.
- Complete process-runner file: `79 passed in 108.03s`.
- A live read-only invocation of
  `_assert_safe_local_git_configuration(Path.cwd())` returned
  `live_git_config_preflight=passed` on this repository.

## 2026-07-30 completed Codex-only dogfood

- Owner-selected workflow:
  `15eb868faf1c5365044adb37f49895ff`.
- Ordered phases:
  `preflight -> mutation -> proof -> security_review -> verification ->
  integration -> complete`.
- The authority omitted peer actions, the plan omitted `plan_peer` and
  `cross_review`, and no peer admission exists. The governed workflow therefore
  had no Claude invocation path and spent no Claude quota. This is a statement
  about this Drydock workflow, not process monitoring for the whole machine.
- Isolated candidate commit:
  `2d048f066ba64fa987a766bfea277a9f0f425712`.
- Exact executable-surface fingerprint:
  `726632f961b5febe7807cc6b472a8e4429bc5af1ef74d9aeae10d7efcaca0eb7`.
- Candidate packet-evidence fingerprint:
  `9fc5ece8e2519cb47517a0a272454392b817d06dd65243868d7380c59753a824`.
- The candidate changed exactly the three authorized skill, regression-test,
  and operator-guide paths. Their Git blob IDs matched the previously reviewed
  candidate exactly.
- Focused candidate regression:
  `30 passed, 1 skipped in 12.16s`.
- Full required suite record:
  `fdb995f6c793e9bc3ef75dea132fe9a08693cc23691acb4602d17b9721818c6c`.
  All eight required commands exited zero against the exact executable
  fingerprint; the run took `257.281` seconds and its output SHA-256 is
  `30f536ff92fac7457f459a2c706f3c283b062464cd232ed415a219af8b12a518`.
  The record is user-writable, unauthenticated, and does not attest execution
  provenance.
- Candidate-bound LaunchGuardian record:
  `8d703ec550ad0f247d40b3fc07165ab1b91a51c7ad10939c3294c16abe1963fc`.
  LaunchGuardian `0.2.0` returned `APPROVED`; all five expected scanners ran,
  each reported zero blocking findings, and the Owner checkout stayed
  unchanged.
- Separate read-only verifier: `PASS`, runner `ok: true`, stage `complete`,
  exit `0`, no timeout, no parse error, tree unchanged, and candidate
  unchanged. Its exact structured-result SHA-256 is
  `ab4fd3f5c249f97a34c3c755e0e4124a1e0b98182a38c077b22bdbfa33c4193c`.
  It used the same model family and reported `epistemic_independence: false`.
- Runner-owned fast-forward integration moved the Owner branch from
  `a94b5221ff3c35a5ef7fe8b3d42688bcbaa9fcf1` to the exact candidate commit.
  The integration result SHA-256 is
  `afbfe705c5d2ba94de0495be1f406e93f04cbc0904ff9b9364be820f2c99c701`;
  no push occurred.
- Workflow terminal state: `complete`, with five admitted execution phases,
  zero procedural failures, and no open circuit. Provider cost is not known
  from trustworthy account evidence and is not reported as zero.
- Non-self-inclusive packet-evidence-parent fingerprint, computed after the
  final task state and verifier record while excluding this
  `verification.md` report:
  `67b4526fa95b326520f1c84e4d9ff310ad38c9cc1f9d11819899ec4d4f069c0e`.
