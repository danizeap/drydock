# Integrated Codex-host dogfood plan

## Goal

Exercise the complete Codex-hosted Drydock workflow on one small, real,
review-derived correction without changing the trusted hook runtime digest.

## Proposed mutation

Add the following exact known-limitation note to the Codex host section of
`docs/AI_OPERATOR_GUIDE.md`:

> Known tested-host limitation (Codex CLI `0.146.0-alpha.3.1`, Windows 11 Pro
> `10.0.26200` build `26200`, Python `3.14.0`, locale encoding `cp1252`): the
> current `py -3 -I -S` inline verifier reads hook stdin through the
> interpreter's locale-decoded text stream before re-encoding it as UTF-8 for
> the verified runtime. Direct probes against handler `a04cf380...` accepted
> ASCII and an em-dash payload but denied a U+0081 payload (UTF-8 bytes
> `c2 81`) with the generic runtime-integrity message while the runtime digest
> remained unchanged. Cp1252-mappable non-ASCII bytes may be silently
> transformed; the reviewer found no decision flip in the current ASCII policy
> patterns, which is not proof that all non-ASCII decisions are unaffected.
> The U+0081 case failed closed and created no false green, but the generic
> message did not establish an integrity failure. Explicit UTF-8 byte decoding
> and separate decode/parse versus integrity failure reasons remain tracked
> follow-ups.

The mutating worker must insert that wording verbatim rather than rewriting it.

## Evidence basis

- Source: `adapters/codex/drydock/scripts/build_hooks.py` constructs the inline
  verifier with `original=sys.stdin.read()` and later
  `original.encode('utf-8')`; it does not specify the initial stdin encoding.
- Review artifact:
  `sdd-plus/changes/codex-host-mvp/claude-final-readiness-review-result.md`
  records the repository-aware peer's reproduced diagnosis and bounded
  findings.
- Current-machine measurement under the hook's Windows interpreter:
  `py -3 -I -S` reports Python 3.14.0, `isolated=1`,
  `ignore_environment=1`, `utf8_mode=0`, and stdin/preferred/locale encoding
  `cp1252`; `PYTHONUTF8` and `PYTHONIOENCODING` were unset. The console code
  page was 437, which is recorded separately rather than conflated with the
  Python locale encoding.
- Direct installed-definition reproduction against handler `a04cf380...`:
  ASCII and em-dash apply_patch payloads returned exit 0 with no denial;
  U+0081 encoded as UTF-8 `c2 81` returned exit 0 with the exact generic
  runtime-integrity deny. Runtime SHA-256 before and after remained
  `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
- UTF-8 bytes `e2 80 94` for an em dash decode under cp1252 as mojibake. The
  current policy patterns are ASCII and the peer found no decision flip; this
  is bounded evidence, not universal proof.

## Scope boundary

The mutating worker is instructed to edit only `docs/AI_OPERATOR_GUIDE.md`. The
runner prevents writes outside its dedicated worktree root; the one-file limit
inside that root is detective, not preventive. Codex rejects the result unless
the extracted changed-file set is exactly `docs/AI_OPERATOR_GUIDE.md`. The
worker must not edit hook/runtime source, generated definitions, tests, specs,
packet evidence, Git metadata, personal plugin state, or any other file. It
must not stage, commit, merge, push, deploy, publish, archive, or release.

Codex remains the control-plane pilot. Claude is a read-only planning and
cross-review peer. The mutation runs through
`adapters/codex/drydock/scripts/process_runner.py mutate` in its dedicated
worktree. The worker result is a non-green handoff until deliberate
cross-review and a separate `process_runner.py verify` verdict.

The runner fixes empty MCP servers, disabled web search and direct network,
ignored repository rules, disabled plugin/app/browser/computer-use features,
an ephemeral workspace-write process, and the dedicated worktree root. These
are requested/tested host boundaries, not full host isolation. After the
runner releases its lease, Codex schedules no second writer and checks the
captured worktree fingerprint again before review and verification; this is
detection rather than continuing exclusive prevention.

The only authorized outward action is a deliberate push of the integrated,
verified documentation commit to remote `origin`, branch
`codex/codex-host-mvp-checkpoint`. The Owner's requested end-to-end workflow
already names push as its terminal action. Release, archive, merge to another
branch, publication, deployment, and personal plugin changes remain
unauthorized.

## Acceptance evidence

1. Claude returns a schema-valid plan critique with no blocking concern.
2. Before mutation, Codex records passing `git diff --check`,
   `python scripts/check_sync.py`, and
   `python scripts/sdd.py verify codex-host-mvp`, plus runtime SHA-256
   `a04cf380...`.
3. The mutation runner reports the Owner checkout and Git control fingerprints
   unchanged, its lease released, `merged: false`, and exactly the allowed
   documentation file changed.
4. Codex inspects the full diff against this plan, byte-compares the inserted
   note with the frozen wording, and confirms no claim exceeds
   the reproduced mechanism.
5. Claude cross-reviews the exact diff as untrusted data and reports no blocker.
6. A separate read-only verifier binds its verdict to the exact worktree state
   and returns PASS.
7. Codex deliberately integrates only the reviewed documentation diff, verifies
   that the integrated doc bytes equal the verified worktree doc bytes,
   commits locally, and then runs a second separate read-only verifier against
   the clean integrated commit before any push.
8. Codex reruns `git diff --check`, `python scripts/check_sync.py`,
   `python scripts/sdd.py verify codex-host-mvp`, and the runtime digest check
   on the integrated commit. Only then does it push the named branch.
9. Packet evidence records every boundary and keeps release, archive, merge,
   publication, deployment, and personal plugin changes unauthorized except
   for the single deliberate documentation integration and branch push named
   above.
