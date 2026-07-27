# Final Claude readiness and live-dogfood review result

## Scope and identity

- Review route: Owner-relayed existing Claude chat with repository access.
- Requested peer: Claude Opus 5.
- Prior accepted correction tip: `79cb83f`.
- Reviewed implementation/evidence tip:
  `f1d9d9b3941f52f89a35cc6575a296f3fbd88848`.
- Checked-out metadata-only descendant:
  `29f4b69189fc18cb2983a447c191122cb53202d6`.
- Identity result: `79cb83f` is an ancestor of `f1d9d9b`, which is an
  ancestor of `29f4b69`; the only later changes were the relay and failed
  transport evidence. No later source, test, spec, or implementation change
  was present.
- Verdict: `converged: true`.
- Blocking concerns: none.

The manual relay does not provide the controller's successful-envelope
`modelUsage` proof. The review is recorded as an Owner-relayed Claude peer
verdict, not as a successful automated-controller model observation.

## Reproduced evidence

- Focused hook/readiness tests: `37 passed, 1 skipped`.
- Full Codex adapter tests: `109 passed, 2 skipped`.
- Root/scaffold sync: 11/11.
- Packet before this verdict: 38 complete, 2 pending.
- All eight generated hook command variants decoded to one expected runtime
  digest matching `runtime.py`, the runtime manifest, the hook description,
  and handler
  `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
- The reviewer verified from code that fresh activity owns model/permission
  evidence, probe recognition is tokenized, the activity write follows all
  deterministic allow checks, apply_patch cannot mark activity, linked and
  junctioned paths reject, and the time window is inclusive at the documented
  bounds.
- The readiness result retains `active: false`, `trusted: unknown`,
  `managed: unknown`, empty covered paths, and
  `ready_for_enforcement: false`.

## New non-blocking findings

1. The previously unexplained integrity denial is a locale-decoding failure.
   The bootstrap launches Python with `-I -S`; isolated mode implies `-E`, so
   `PYTHONIOENCODING` and `PYTHONUTF8` cannot pin stdin. `sys.stdin.read()`
   therefore uses the host locale. On this cp1252 machine, an undefined byte
   raises before policy execution and the broad bootstrap exception emits the
   generic runtime-integrity denial. The reviewer reproduced ASCII allow,
   silently mis-decoded em-dash allow, and a `C2 81` input denial while the
   runtime digest stayed unchanged. This fails closed and creates no false
   green, but the message asserts an integrity cause it did not establish.
2. Bytes that cp1252 can map may be decoded and re-encoded differently before
   policy evaluation. Current policy patterns are ASCII, so the reviewer found
   no decision flip, but the runtime is not evaluating the host's exact
   non-ASCII text.
3. Probe labeling is forgeable within the already cooperative boundary:
   tokenized commands such as an echo containing the expected script,
   subcommand, and flag can receive `probe_kind: readiness_cli` even when the
   readiness CLI did not execute. Integrity-verified handler liveness remains
   true; the label is stronger than the mechanism.
4. Native unquoted Windows backslash paths are a fail-closed false negative
   because POSIX `shlex` consumes backslashes. A genuine probe may run while
   readiness remains unavailable.
5. The stale Desktop backend behavior remains point-in-time reported evidence.
   The reviewer verified its internal consistency but could not independently
   reproduce Desktop reload behavior.

## Preserved risks

- Evidence is point-in-time on Codex CLI `0.146.0-alpha.3.1`, beta permission
  profiles, and non-managed user-disableable hooks.
- Wall-clock freshness and unsigned user-writable plugin data permit the
  disclosed in-window replay and cooperative record fabrication.
- Locale-specific denial bytes vary across machines until UTF-8 is pinned.
- Two automated peer calls exhausted their budget ceiling without a verdict;
  the manual relay carried this gate.
- One integrated end-to-end hosted workflow remains pending. This peer verdict
  does not authorize merge, archive, publication, release, deployment, or a
  personal plugin change.

## Required non-blocking follow-ups

1. Read stdin bytes and decode UTF-8 explicitly under `-I -S`.
2. Separate payload decode/parse failures from runtime-integrity failures while
   keeping both fail-closed.
3. Add a regression for an input byte undefined in the host locale.
4. Tighten probe recognition to the executed program and describe
   `probe_kind` as a cooperative label.
5. Use Windows-appropriate tokenization for native backslash-path probes.

These findings remain tracked; they are not silently waived or promoted into
current enforcement claims. They do not reopen the peer gate because the
reviewer found no false green or blocking concern in the scoped MVP.
