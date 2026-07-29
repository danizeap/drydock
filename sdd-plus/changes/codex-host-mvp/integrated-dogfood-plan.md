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
`cba390733d524eeaea518b8b7372ad7d06d9f7bb` (48,968 LF-only bytes, raw
SHA-256 `0321b034d8e9b3b7939560f0c75ff4d056ad2b5dcd7d03ecea8f482d2ffa1dff`).
The unique `Readiness may call` anchor begins at byte offset 12,413 and is
already preceded by `0a 0a`. Immediately before that anchor, the worker inserts
the 1,255 frozen note bytes followed by one additional `0a`; the 1,256-byte
insertion therefore has SHA-256
`7c9e5c45e0de3fb0e4cd71ab0dd020f9af1e721d96c887952a807d25104f349e`.
The note's terminal `0a` plus the added `0a` form the blank line after it; the
existing two `0a` bytes form the blank line before it. The expected
post-mutation linked-worktree file is 50,224 LF-only bytes with raw SHA-256
`70ec25349799865c9596ea413156f53f20a2937e3690573d2737996f158ae29c`
and normalized Git blob SHA-1
`0093b7d1602e5e1b9ffbb3947d34d128eb87f74e`.

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
  representation (49,217 bytes, raw SHA-256
  `23276c3e9e71ccc31da76b038479fe1fe2640a5e6f121d8df62e0a05453e22c7`)
  of the same normalized blob. Worker acceptance uses the LF-only linked
  worktree commitment above. Integration acceptance separately requires the
  exact inserted block and the expected normalized blob; it does not
  misdescribe pre-existing working-tree EOL representation as mutation drift.
- The prior frozen preimage `31b5995c...a7f` is stale because later reviewed
  orchestration-efficiency commits appended 99 lines after the unchanged
  insertion anchor. The note remains absent, the unique anchor remains at byte
  offset 12,413, and the current preimage/postimage values above were
  recomputed from exact committed blob bytes. No worker may start until a fresh
  peer critique accepts this rebased plan.
- Both instruction anchors are unique in the current committed blob: the
  complete preceding paragraph ending with `context.` occurs once, and
  `Readiness may call` occurs once. The worker instruction identifies the
  unique following anchor; the complete preceding and following paragraphs are
  included verbatim below for peer content review.
- The stable anchor is deliberately splice-driven. Its location is not the
  ideal narrative home for the limitation, but changing the already frozen
  bytes or anchor would invalidate the registered splice and consume another
  review cycle. The one-long-line form is also deliberate: it is the frozen
  artifact, not transport reflow. Packet evidence records both dispositions
  and leaves any later relocation or hard-wrapping to a separately governed
  follow-up.
- The host/version tuple is point-in-time evidence even though the frozen
  paragraph carries no calendar date. It is bound here to this packet, the
  final `base_commit`, and the pre-mutation interpreter/runtime recheck; it is
  not a perpetual statement about later Codex, Windows, or Python versions.

## Existing runner safeguards relevant to the peer concern

- `WorktreeBoundary` stores the linked worktree `.git` pointer SHA-256, and
  `_assert_worktree_boundary` checks it before every `_run_worktree_git` call.
- Post-worker Git uses explicit `--git-dir` and `--work-tree`, an absolute Git
  executable, pinned configuration, and a controlled environment.
- The runner already pins `core.hooksPath` to the null device,
  `core.fsmonitor=false`, `diff.external=` and `--no-textconv`; scrubs inherited
  `GIT_*`; nulls global and system Git config; and includes the complete bounded
  common `.git/hooks` directory in `git_control_fingerprint`. Round 1's claim
  that hooks were outside every fingerprint was therefore not adopted. The
  later control-plane commit and push are separate commands and must repeat the
  null hooks/fsmonitor/external-diff pins plus `--no-verify`.
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

The runner requests empty MCP servers, disabled web search and network-enabled
features, ignored repository rules, disabled plugin/app/browser/computer-use
features, an ephemeral workspace-write process, and the dedicated worktree
root. Those are requested argv/profile boundaries, not proof that the host
made no connection attempt and not full host isolation. After the runner
releases its lease, Codex schedules no second writer and checks the captured
worktree fingerprint again before review and verification; this is detection
rather than continuing exclusive prevention.

The prior live mutation child emitted a failed `DELETE` cleanup attempt for a
Render MCP session despite the empty-MCP and disabled-feature argv contract.
The attempt was emitted by host/session cleanup after the bounded worker turn,
not by a task-authorized tool call; the closed channel is not evidence that a
remote resource changed. Its deeper host source and personal-state dependency
remain unproven. This is accepted positive counterevidence to a no-egress claim:
the run claims only requested argv/profile configuration and does not claim
direct-network denial, zero MCP transport, zero connection attempts, or
non-contact with personal Codex state. The task contains only the public
operator-guide paragraph and no secret-bearing content. The complete worker
event/result stream is retained as an acceptance artifact and any host-reported
MCP/network attempt is recorded; absence of a reported attempt remains
`unknown`, never proof that none occurred.

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
here. The current v2 proof preflight separately blocks tracked bytecode and
ignored `conftest.py`, `sitecustomize.py`, `usercustomize.py`, and `*.pth`
injection paths. This is enumerative coverage, not proof that every possible
ignored injection path has been classified. Ordinary ignored bytecode caches
are disclosed but do not block because the full required suite runs from a
fresh exact-commit materialization with bytecode writes disabled.

`verify()` does not itself call `_assert_safe_local_git_configuration()`.
`mutate()` called that precheck immediately before creating the linked
worktree. Calling it again after creation is not a valid mechanism in this
repository: Git rejects `config --worktree` when multiple worktrees exist and
`extensions.worktreeConfig` is not enabled. Before verification, Codex instead
revalidates the linked `.git` pointer, requires the captured Git-control
fingerprint to equal the value recorded before worker launch, and directly
parses every local/worktree config file named by `GitControlBoundary` with
`git config --file <exact-path> --no-includes --null --list`. This is an
allow-list, not a deny-list. `common/config` must contain exactly the
pre-recorded key/value multiset whose permitted keys are
`core.repositoryformatversion`, `core.filemode`, `core.bare`,
`core.logallrefupdates`, `core.symlinks`, `core.ignorecase`,
`remote.origin.url`, `remote.origin.fetch`, and the pre-existing
`branch.<exact-recorded-name>.(remote|merge)` entries for `main`,
`codex/codex-host-mvp-checkpoint`, `codex/peer-unavailable-governance`,
`codex/adaptive-delegation-ledger`,
`codex/orchestration-efficiency-hardening`, and
`codex/claude-usage-signal-round1`. `common/config.worktree`,
`owner/config.worktree`, and `worker/config.worktree` must remain absent. Any
unexpected key, value, duplicate, file, or absence is a mismatch and aborts.
This structurally excludes, among everything else, `include.*`,
`includeIf.*`, `filter.*.(clean|smudge|process)`,
`url.*.(insteadOf|pushInsteadOf)`, `credential.helper`, `core.hooksPath`,
`core.fsmonitor`, `core.sshCommand`, `core.gitProxy`, `diff.external`,
`diff.*.textconv`, `http.proxy`, `http.*.proxy`, `protocol.*.allow`,
`remote.*.pushurl`, `remote.*.receivepack`, `remote.*.uploadpack`, and
`alias.*`.
That preserves the pre-launch safe-config result without claiming an unusable
post-creation helper call. The current verifier also refuses a dirty or
unproven candidate before provider discovery. After cross-review, the Codex
control plane therefore commits only the exact reviewed documentation diff on
the isolated branch, runs one `full_required_suite` proof from a fresh
materialization of that exact commit, and invokes the first verifier against
the now-clean retained worktree, never the Owner checkout, with the exact
shape:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
Get-Content -Raw <verification-request> |
  & 'C:\Users\Daniel Paez\AppData\Local\Programs\Python\Python311\python.exe' `
    -B adapters/codex/drydock/scripts/process_runner.py verify `
    --repo <exact-mutation-worktree> `
    --model gpt-5.6-sol `
    --packet-root sdd-plus/changes/codex-host-mvp `
    --proof-record <exact-full-required-suite-proof-record> `
    --timeout 600
```

The proof record is user-writable identity evidence, not authenticated
provenance or independent attestation. The verifier must audit the candidate
and may not execute the recorded command. Parent-side proof admission binds
the exact schema-v2 record to the freshly recomputed v2 executable fingerprint
before provider discovery; a missing, malformed, stale, intermediate, failed,
timed-out, nonzero, or fingerprint-mismatched record refuses verification.
The remaining proof trust base is the integrity of the local filesystem and
the control-plane processes reading it. The record does not defend against an
actor able to forge both repository bytes and the local proof artifact.

The control-plane interpreter above is the current absolute Python 3.11.9
executable and is distinct from the hook's tested `py -3 -I -S` Python 3.14.0
interpreter. All control-plane Python calls for this run use `-B` and
`PYTHONDONTWRITEBYTECODE=1` so their own bytecode caches cannot trip the
ignored-artifact gate.

The hook interpreter is point-in-time state, not implied by the `py -3`
launcher forever. Immediately before mutation, Codex records the resolved path
`C:\Users\Daniel Paez\AppData\Local\Python\pythoncore-3.14-64\python.exe`,
version `3.14.0`, `stdin_encoding: cp1252`, and `utf8_mode: 0` alongside the
runtime digest. Any change is recorded and forces a fresh claim review if it
invalidates the note; absence of a change is not generalized beyond this run.

The only authorized outward action is a deliberate push of the integrated,
verified documentation commit to remote `origin`, branch
`codex/codex-host-mvp-checkpoint`. The Owner's requested end-to-end workflow
already names push as its terminal action. Release, archive, merge to another
branch, publication, deployment, and personal plugin changes remain
unauthorized.

The expected configured push URL is the literal
`git@github-personal:danizeap/drydock.git`; the current SSH resolution must
report host `github.com`, user `git`, and port `22`, with `ProxyCommand` and
`ProxyJump` absent. Before mutation and again immediately before push, Codex
resolves the push URL in an environment that scrubs inherited `GIT_*`, nulls
global/system Git config, and applies the exact config allow-list above. The
current resolved identity file is
`C:\Users\Daniel Paez\.ssh\id_ed25519_personal`; a changed, missing, or
additional identity is recorded and blocks until reviewed.

The ambient SSH resolution currently reports `StrictHostKeyChecking ask` and
`UpdateHostKeys yes`, so the push must not inherit those values. The single
push invocation pins `BatchMode=yes`, `HostName=github.com`, `User=git`,
`Port=22`, `ProxyCommand=none`, `ProxyJump=none`,
`StrictHostKeyChecking=yes`, `UpdateHostKeys=no`,
`GlobalKnownHostsFile=NUL`, the exact resolved identity with
`IdentitiesOnly=yes`, and the exact existing
`C:\Users\Daniel Paez\.ssh\known_hosts` as `UserKnownHostsFile`. Before the
push, Codex records that file's digest and its exact `github.com` fingerprints;
the current baseline is ED25519
`SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`, RSA
`SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s`, and ECDSA
`SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM`. Verbose SSH output from
the same push must identify the server host-key fingerprint actually accepted
and it must equal one of that exact recorded set. If the push reports success
but this fingerprint is absent or different, the run stops without retry or
ref rewrite and reports the outward result as unproven.

The control-plane commit and push also pin `core.hooksPath` to an empty exact
directory, `core.fsmonitor=false`, `diff.external=`, and
`credential.helper=`, and use `--no-verify`; the push URL must still equal the
registered literal. The runner's own extraction keeps its existing stronger
pinned Git wrapper.

The repository is publicly readable at `https://github.com/danizeap/drydock`.
At current remote checkpoint
`ae9735511fade16780f78435213f5047a32e3900`, the exact remote branch already
contains `claude-final-readiness-review-result.md`,
`integrated-dogfood-negotiation.md`, and `decision-log.md`, and the last file
contains the locale-decoding finding and the exact tested-host environment
tuple that the new guide paragraph repeats. Those facts are rechecked
immediately before push; a mismatch or unconfirmable visibility stops before
the outward action.

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
not from this plan. Before the push command is constructed, packet evidence
must contain the verbatim authorizing utterance, both its Owner-authored and
raw user-role turn positions in the current task, its exact remote/branch, and
an assertion that no later Owner turn narrowed or revoked it. The current
artifact is in `integrated-dogfood-negotiation.md` under
`Current-task push authorization artifact`. If any later Owner turn exists,
Codex must compare it before constructing the command; ambiguity or a narrowing
instruction stops at the local commit. Updating this evidence after proof
changes the candidate and therefore requires fresh exact-candidate proof and
verification rather than a stale push.

If push reports success but the remote SHA cannot be confirmed or differs, the
run does not retry, force, delete, or rewrite any ref. It stops and returns to
the Owner with the local commit, exact push output, and observed or
unconfirmable remote state.

The locale-decoding remediation is already tracked outside this one-file
mutation in `decision-log.md` under `PEER-DIAGNOSED GAP`: explicit UTF-8 byte
decoding, failure-taxonomy separation, a byte-level regression, executed-
program probe recognition, and Windows tokenization remain follow-ups.

## Acceptance evidence

1. Claude returns a schema-valid plan critique with no blocking concern.
2. Before mutation, Codex records passing `git diff --check`,
   `python scripts/check_sync.py`, and
   `python scripts/sdd.py verify codex-host-mvp`, plus runtime SHA-256
   `a04cf380...`, the resolved hook interpreter path/version/encoding above,
   `git check-attr text eol -- docs/AI_OPERATOR_GUIDE.md`, the complete Git
   config allow-list result, and the sanitized effective push URL/SSH
   destination. The exact clean HEAD after Round-2 evidence is recorded as the
   sole worktree `base_commit`.
   Immediately before worktree creation, Codex asserts
   `git rev-parse <base_commit>:docs/AI_OPERATOR_GUIDE.md` equals
   `cba390733d524eeaea518b8b7372ad7d06d9f7bb`, recomputes the unique
   `Readiness may call` anchor at byte offset 12,413, and independently
   re-derives the registered 50,224-byte postimage and both hashes. Any
   mismatch aborts to a fresh plan round; values are never recomputed into a
   new mid-run contract.
3. The mutation runner reports the Owner checkout and Git control fingerprints
   unchanged, its lease released, `merged: false`, and exactly the allowed
   documentation file changed.
4. Codex inspects the full diff against this plan, compares both the raw
   linked-worktree file SHA-256 against `70ec2534...` and the normalized Git blob
   produced by `git hash-object --path docs/AI_OPERATOR_GUIDE.md` against
   `0093b7d...`, and confirms no claim exceeds the reproduced mechanism. Any
   mismatch aborts rather than being waived as line-ending noise.
5. Claude cross-reviews the exact diff as untrusted data, receiving the
   inserted note text plus both adjacent paragraphs, and reports no semantic,
   placement, or claim-calibration blocker. The peer is not asked to attest
   transport bytes or recompute a digest. Codex alone extracts the exact note
   byte sequence placed in the cross-review input, records its byte count and
   SHA-256, and requires equality with the frozen 1,255-byte artifact and
   `950be9d7...91e65`; a transport delta is a blocker, not a peer waiver. A
   content rejection stops the run, freezes no replacement in-place, and
   returns to plan review with a newly hashed note; neither the worker nor
   controller edits the rejected text opportunistically.
6. The control plane commits only the reviewed one-file diff on the isolated
   branch, then `proof-run --scope full_required_suite` runs the required
   legacy, Codex-adapter, root/scaffold, bundle, hook, release-version, and
   packet-verification checks from a fresh materialization of that exact
   commit. Every step must return zero and the resulting schema-v2 proof record
   must be accepted for the exact current executable fingerprint without being
   described as authenticated or provenance-attested.
7. A separate read-only verifier returns PASS against that clean isolated
   commit with the accepted proof record and freshness/anti-replay state
   binding. Immediately before and after it, Codex requires no ignored
   code-injection path, no `.git` pointer or Git-control drift, no unsafe key
   in the directly parsed config files, and no candidate-fingerprint mismatch.
   The unusable post-creation `_assert_safe_local_git_configuration()` call is
   not reported as a passing check, and ordinary ignored bytecode caches are
   not relabelled as absent.
8. Before moving the Owner branch, Codex creates a second fresh, clean,
   detached materialization of the exact reviewed isolated commit and verifies
   there that the 1,256-byte insertion, normalized Git blob, executable
   fingerprint, packet-evidence fingerprint, and
   `git check-attr text eol -- docs/AI_OPERATOR_GUIDE.md` equal the first
   verified worktree values. A second separate read-only verifier then runs
   against that exact fresh materialization and accepted proof record. It adds
   a second freshness/anti-replay binding to the exact candidate commit, not an
   independent judgment or corroborating vote. Verifier #2 uses the same
   separate ephemeral `read-only` sandbox, disabled features, absolute Python
   3.11.9 interpreter, `-B`, packet root, proof record, and timeout as verifier
   #1, with this exact target shape:

   ```powershell
   $env:PYTHONDONTWRITEBYTECODE = '1'
   Get-Content -Raw <second-verification-request> |
     & 'C:\Users\Daniel Paez\AppData\Local\Programs\Python\Python311\python.exe' `
       -B adapters/codex/drydock/scripts/process_runner.py verify `
       --repo <second-fresh-exact-candidate-materialization> `
       --model gpt-5.6-sol `
       --packet-root sdd-plus/changes/codex-host-mvp `
       --proof-record <exact-full-required-suite-proof-record> `
       --timeout 600
   ```

   Immediately before and after verifier #2, that materialization must be
   clean at the exact candidate commit, ignored code-injection paths must be
   absent, and both repository fingerprints must be unchanged. A verifier
   non-PASS or comparison failure leaves the Owner branch at the recorded base
   commit and stops with the isolated commit, branch, and worktree paths
   reported; no recovery or rollback is needed because integration has not
   occurred.
9. Only after both verifiers and every pre-integration comparison pass does
   Codex deliberately fast-forward the clean, unchanged Owner branch from the
   recorded `base_commit` to the exact twice-verified candidate commit. It then
   requires the actual Owner `HEAD`, normalized Git blob `0093b7d...`,
   executable fingerprint, packet-evidence fingerprint, insertion bytes, and
   attributes to equal the verified values. The normalized committed blob is
   authoritative. Raw on-disk EOL representation and digest are recorded; a
   raw EOL-only delta is not misreported as content drift, but any normalized
   blob mismatch blocks. Codex then reruns `git diff --check`,
   `python scripts/check_sync.py`, `python scripts/sdd.py verify
   codex-host-mvp`, and the runtime digest check on the integrated commit. Only
   then may it construct and execute the named push.
10. Packet evidence records every boundary, that the planning peer received
    pasted excerpts rather than repository access, that the hostile-pointer
    regression uses a fake worker and bounded mutation shapes, and that the
    Codex verifier reports `epistemic_independence: false`. It also records that
    personal Codex configuration is trusted residual state, not recursively
    fingerprinted by this run, and that the proof gate ultimately trusts the
    local filesystem. Any host-reported inbound worker payload is retained; if
    none is reported, inbound activity remains unknown rather than absent.
    Regardless of source, an inbound influence that changes output is bounded
    by the exact 50,224-byte postimage gate. It keeps release, archive, merge,
    publication, deployment, and personal plugin changes unauthorized except
    for the single deliberate documentation integration and branch push named
    above.

Any mismatch, extra tracked/untracked file, blocked ignored injection path,
peer blocker, verifier non-PASS, failed gate, digest drift, remote-tip drift,
or byte-comparison failure aborts before integration or push. Before
integration, the reviewable worktree is retained for inspection and cleanup is
not forced. After a local commit, failure stops before push and returns to the
Owner; no destructive reset or automatic rollback is authorized.

## Peer-visible frozen content

The planning and cross-review peers receive this content for semantic review,
not only its digest. Codex separately byte-binds the transported middle
paragraph to the 1,255-byte frozen note; the first and third paragraphs are the
unique adjacent committed guide context. The peer does not attest transport
bytes or repository digests.

```text
The current `model` and `permission_mode` evidence comes from the fresh
PreToolUse activity record. The older SessionStart record remains only the
packet-fingerprint baseline and is not presented as current model/permission
context.

Known tested-host limitation (Codex CLI `0.146.0-alpha.3.1`, Windows 11 Pro `10.0.26200` build `26200`, Python `3.14.0`, locale encoding `cp1252`): the current `py -3 -I -S` inline verifier reads hook stdin through the interpreter's locale-decoded text stream before re-encoding it as UTF-8 for the verified runtime. Direct installed-definition probes accepted ASCII and an em-dash payload in both current locale mode and forced UTF-8 mode; U+0081 (`c2 81`) and U+008D (`c2 8d`) were denied with the generic runtime-integrity message only in locale mode and were allowed with the otherwise identical `-X utf8=1` verifier. Static byte-flow inspection confirms the accepted em-dash bytes are transformed by the cp1252 decode and UTF-8 re-encode before policy evaluation. The current policy patterns are ASCII and no decision flip was reproduced, which is not proof that every non-ASCII decision is unaffected; any future non-ASCII policy pattern would be evaluated against transformed text until this is fixed. The undefined-byte cases failed closed and created no false green, but the generic message did not establish an integrity failure. Explicit UTF-8 byte decoding and separate decode/parse versus integrity failure reasons remain tracked follow-ups.

Readiness may call `claude auth status --json`, which spends no model quota.
`auth_ready` proves only authentication; `operational_ready` requires a
successful schema-validated live peer round. Claude is optional: its absence
removes cross-model agreement, not Codex-hosted lifecycle governance.
Single-pilot continuation is fail-closed to four proven benign availability
cases: authentication unavailable before provider spawn, an exact supported
rate-limit marker, timeout with bounded cleanup, or a bare non-zero exit with
no subtype/contract output plus requested-model evidence and finite
`total_cost_usd` exactly equal to zero. The pilot may then continue the ordinary
packet, approval, mutation, review, and verification gates in `single_pilot`
mode while reporting `peer_convergence: not_established`. This is continuity
of governance, not a substitute claim of cross-model agreement. Budget
ceilings, policy/refusal/context-limit failures, unknown structured subtypes,
malformed output, model mismatch, and missing, malformed, negative, or positive
cost instead return `return_to_owner`. Rate limiting is identified only from
exact supported structured markers or explicit rate-limit phrases, not from
generic `rate`, `quota`, or `usage` substrings.
```
