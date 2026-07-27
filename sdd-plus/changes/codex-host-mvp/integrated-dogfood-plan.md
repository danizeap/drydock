# Integrated Codex-host dogfood plan

## Goal

Exercise the complete Codex-hosted Drydock workflow on one small, real,
review-derived correction without changing the trusted hook runtime digest.

## Proposed mutation

Insert the exact UTF-8/LF bytes from
`sdd-plus/changes/codex-host-mvp/integrated-dogfood-note.txt` as a standalone
paragraph in the Codex host section of `docs/AI_OPERATOR_GUIDE.md`, immediately
after the paragraph ending with "not presented as current model/permission
context." and before the paragraph beginning "Readiness may call".

The note is frozen before mutation. The worker must copy it verbatim without
paraphrasing, reflowing, or editing adjacent prose. `.gitattributes` pins
`docs/AI_OPERATOR_GUIDE.md` to LF even though the Owner's `core.autocrlf` is
true. The comparison basis is the committed LF blob content with no BOM.
The frozen note is 1,255 ASCII bytes with one terminal LF, no CR, and SHA-256
`950be9d72a83dbe662737f855621cb5a02fde4231a70b09f56673373e7991e65`.

The exact splice is pre-registered against committed guide preimage blob
`31b5995c44cc260904e6f2a2f861355c0538ea7f` (42,284 LF-only bytes, raw
SHA-256 `608712760ed1ca2aa7fc3b2a0df24da2e464ecc1c05c885b7efd88a38b79ac12`).
The unique `Readiness may call` anchor begins at byte offset 12,413 and is
already preceded by `0a 0a`. Immediately before that anchor, the worker inserts
the 1,255 frozen note bytes followed by one additional `0a`; the 1,256-byte
insertion therefore has SHA-256
`7c9e5c45e0de3fb0e4cd71ab0dd020f9af1e721d96c887952a807d25104f349e`.
The note's terminal `0a` plus the added `0a` form the blank line after it; the
existing two `0a` bytes form the blank line before it. The expected
post-mutation linked-worktree file is 43,540 LF-only bytes with raw SHA-256
`52444a046b87ea1354250f5c72a3ae1a3654c198262a3f6d1ad4546648ec5cf4`
and normalized Git blob SHA-1
`5b47ca2302e5bb66312a07ebe8f43b0dca2c820c`.

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
  current locale mode and an otherwise identical verifier with
  `-X utf8=1` both allowed ASCII and em-dash payloads. Locale mode denied
  U+0081 (`c2 81`) and U+008D (`c2 8d`) with the generic integrity reason;
  forced UTF-8 mode allowed both. Each pair used identical payload bytes and
  payload SHA-256. Runtime SHA-256 before and after remained
  `a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
- Static byte flow is explicit: `build_hooks.py` first decodes through
  `sys.stdin.read()`, then feeds
  `original.encode('utf-8')` to the verified runtime. UTF-8 bytes `e2 80 94`
  decode under cp1252 as mojibake and re-encode to different bytes. The current
  policy patterns are ASCII and no decision flip was reproduced; future
  non-ASCII policy patterns would be evaluated against transformed text until
  the bootstrap is fixed. This is bounded evidence, not universal proof.
- The frozen note and the adjacent insertion-anchor text are ASCII-only. If
  the live hook reports a locale/decode or integrity denial while applying
  this mutation, the workflow stops; it does not rephrase, bypass, disable, or
  retry the mutation through another tool path.
- `git check-attr text eol -- docs/AI_OPERATOR_GUIDE.md` reports `text: auto`
  and `eol: lf`; `.gitattributes` is committed with `* text=auto eol=lf`.
  No tracked `.gitmodules` file or configured submodule is present.
- `scripts/check_sync.py` has an explicit 11-entry `PAIRS` list and does not
  include `docs/AI_OPERATOR_GUIDE.md`; the guide is neither a sync mirror nor a
  generated packet artifact. A one-file guide mutation therefore does not
  conflict with the sync gate.
- The Owner checkout's clean on-disk guide preimage is a mixed-EOL
  representation (42,534 bytes, raw SHA-256
  `5b877ee7132f7c6db0a9f419808dace623c511c0552597d359b38a9c6fb7853f`)
  of the same normalized blob. Worker acceptance uses the LF-only linked
  worktree commitment above. Integration acceptance separately requires the
  exact inserted block and the expected normalized blob; it does not
  misdescribe pre-existing working-tree EOL representation as mutation drift.

## Existing runner safeguards relevant to the peer concern

- `WorktreeBoundary` stores the linked worktree `.git` pointer SHA-256, and
  `_assert_worktree_boundary` checks it before every `_run_worktree_git` call.
- Post-worker Git uses explicit `--git-dir` and `--work-tree`, an absolute Git
  executable, pinned configuration, and a controlled environment.
- `git_control_fingerprint` covers common, Owner, and worker Git control paths
  before launch, after process-tree shutdown, and after extraction. Drift
  refuses later evidence.
- `_extract_changes` uses a temporary index/object directory plus `git add -A`
  to capture tracked and untracked changes. A separate porcelain status with
  `--ignored=matching --untracked-files=all` exposes ignored artifacts, which
  block the handoff.
- `test_worker_git_link_tamper_cannot_redirect_runner_git` covers pointer
  replacement and deletion and proves refusal before redirected Git changes
  the Owner index or object database.
- A real linked-worktree sensitivity probe used
  `C:\Users\Daniel Paez\drydock\.drydock-worktrees\772ec131d9b7`.
  `canonical_repo()` returned that exact linked-worktree root. Its
  `repository_fingerprint()` changed from
  `db0120d86d0540fd9a054b7a3409fd524a8e75a88a1078ed74d24453e81cf852`
  to
  `7e94ffbc6a6b2f5468dfcaa0df6875e2f7c940c806a2871a46bfb6c5e1fff82e`
  when a scratch file was written, then returned exactly to the first digest
  after the file was removed. Bounded cleanup removed the worktree, its branch,
  and its lease without a boundary error.

These targeted controls close the concrete redirect chain. They are not
described as a universal recursive filesystem inventory.

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

The separate verifier is a new ephemeral Codex process with `read-only`
sandbox; hooks, plugins, apps, browser, computer-use, MCP, web search, and
repository rules are disabled. It does not depend on the inline hook verifier
whose locale behavior the note documents. The schema supplies the exact
`HEAD` and `repository_fingerprint` working-tree SHA-256 for freshness and
anti-replay; the verifier's required echo is not described as proof that the
model independently observed those values. The runner recomputes the same
fingerprint after the verifier exits and rejects drift. Tracked, untracked,
and diff bytes enter that fingerprint, and the linked-worktree probe above
proves sensitivity to an added scratch byte on the exact repository shape used
here. Ignored artifacts are separately required absent immediately before and
after verification because they are not part of that fingerprint.

`verify()` does not itself call `_assert_safe_local_git_configuration()`.
Immediately before invoking it, Codex therefore calls that control-plane
precheck and revalidates the linked `.git` pointer plus the captured Git-control
fingerprint. The first verifier is invoked against the retained mutation
worktree, never the Owner checkout, with the exact shape:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
Get-Content -Raw <verification-request> |
  & 'C:\Users\Daniel Paez\AppData\Local\Programs\Python\Python311\python.exe' `
    -B adapters/codex/drydock/scripts/process_runner.py verify `
    --repo <exact-mutation-worktree> --model gpt-5.6-sol --timeout 600
```

The control-plane interpreter above is the current absolute Python 3.11.9
executable and is distinct from the hook's tested `py -3 -I -S` Python 3.14.0
interpreter. All control-plane Python calls for this run use `-B` and
`PYTHONDONTWRITEBYTECODE=1` so their own bytecode caches cannot trip the
ignored-artifact gate.

The only authorized outward action is a deliberate push of the integrated,
verified documentation commit to remote `origin`, branch
`codex/codex-host-mvp-checkpoint`. The Owner's requested end-to-end workflow
already names push as its terminal action. Release, archive, merge to another
branch, publication, deployment, and personal plugin changes remain
unauthorized.

The finding is already present on the same remote branch in
`claude-final-readiness-review-result.md`,
`integrated-dogfood-negotiation.md`, and packet evidence; this operator-guide
note does not newly disclose the weakness outside the repository. Before push,
Codex requires the remote branch tip to equal the recorded integration base or
be an ancestor of the local integrated commit, refuses force flags, and
confirms the remote SHA after the push. This precheck is defense in depth; the
non-force server update is the atomic protection against a concurrent remote
advance.

Push authority comes from the Owner's out-of-band request in this Codex task,
not from this plan: the requested hosted flow explicitly ends
"verifier -> push -> back to me", and the Owner then repeatedly directed Codex
to continue this bounded run. Packet evidence records that chat authorization
as a push precondition. If it cannot be tied to the current task at execution
time, the run stops at the local commit.

The locale-decoding remediation is already tracked outside this one-file
mutation in `decision-log.md` under `PEER-DIAGNOSED GAP`: explicit UTF-8 byte
decoding, failure-taxonomy separation, a byte-level regression, executed-
program probe recognition, and Windows tokenization remain follow-ups.

## Acceptance evidence

1. Claude returns a schema-valid plan critique with no blocking concern.
2. Before mutation, Codex records passing `git diff --check`,
   `python scripts/check_sync.py`, and
   `python scripts/sdd.py verify codex-host-mvp`, plus runtime SHA-256
   `a04cf380...`.
3. The mutation runner reports the Owner checkout and Git control fingerprints
   unchanged, its lease released, `merged: false`, and exactly the allowed
   documentation file changed.
4. Codex inspects the full diff against this plan, compares both the raw
   linked-worktree file SHA-256 against `52444a...` and the normalized Git blob
   produced by `git hash-object --path docs/AI_OPERATOR_GUIDE.md` against
   `5b47ca...`, and confirms no claim exceeds the reproduced mechanism. Any
   mismatch aborts rather than being waived as line-ending noise.
5. Claude cross-reviews the exact diff as untrusted data and reports no blocker.
6. A separate read-only verifier returns PASS with freshness/anti-replay state
   binding to the exact retained mutation worktree. Immediately before and
   after it, Codex requires no ignored artifacts, no `.git` pointer or
   Git-control drift, and no worktree-fingerprint mismatch.
7. Codex deliberately integrates only the reviewed documentation diff, verifies
   that the exact 1,256-byte insertion and normalized Git blob equal the
   verified worktree versions, records the Owner checkout's raw representation
   separately, commits locally, and then runs a second separate read-only
   verifier against the clean integrated commit before any push. Verifier #2
   uses the same separate ephemeral `read-only` sandbox, disabled features,
   freshness/anti-replay state binding, absolute Python 3.11.9 interpreter,
   `-B`, and timeout as verifier #1, with this exact target shape:

   ```powershell
   $env:PYTHONDONTWRITEBYTECODE = '1'
   Get-Content -Raw <post-integration-verification-request> |
     & 'C:\Users\Daniel Paez\AppData\Local\Programs\Python\Python311\python.exe' `
       -B adapters/codex/drydock/scripts/process_runner.py verify `
       --repo 'C:\Users\Daniel Paez\drydock' `
       --model gpt-5.6-sol --timeout 600
   ```

   Immediately before and after verifier #2, the Owner checkout must be clean,
   its actual `HEAD` must equal the local integration commit, ignored artifacts
   must be absent, and the repository fingerprint must be unchanged.
8. Codex reruns `git diff --check`, `python scripts/check_sync.py`,
   `python scripts/sdd.py verify codex-host-mvp`, and the runtime digest check
   on the integrated commit. Only then does it push the named branch.
9. Packet evidence records every boundary, that the planning peer received
   pasted excerpts rather than repository access, that the hostile-pointer
   regression uses a fake worker and bounded mutation shapes, and that the
   Codex verifier reports `epistemic_independence: false`. It also records that
   personal Codex configuration is trusted residual state, not recursively
   fingerprinted by this run. It keeps release, archive, merge, publication,
   deployment, and personal plugin changes unauthorized except for the single
   deliberate documentation integration and branch push named above.

Any mismatch, extra or ignored file, peer blocker, verifier non-PASS, failed
gate, digest drift, remote-tip drift, or byte-comparison failure aborts before
integration or push. Before integration, the reviewable worktree is retained
for inspection and cleanup is not forced. After a local commit, failure stops
before push and returns to the Owner; no destructive reset or automatic
rollback is authorized.
