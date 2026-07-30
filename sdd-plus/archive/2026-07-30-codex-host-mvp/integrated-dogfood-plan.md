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
The frozen note is 1,847 ASCII bytes across 25 hard-wrapped lines, with a
maximum line length of 77, one terminal LF, no CR, and SHA-256
`5bd5e43b85a0cdf1e28923cb36e96d5adc2660d2ca085dc218a65074b91a69cd`.

The exact splice is pre-registered against committed guide preimage blob
`26d659a4e654a02ec9be5cb96f0ddcc750cb6235` (56,629 LF-only bytes, raw
SHA-256 `a9323e8af7d5b951dd00f48034aa568434bc2c46e234f3fd2912e1d6cd5467fc`).
The unique `Readiness may call` anchor begins at byte offset 12,413 and is
already preceded by `0a 0a`. Immediately before that anchor, the worker inserts
the 1,847 frozen note bytes followed by one additional `0a`; the 1,848-byte
insertion therefore has SHA-256
`322ef737828046fa7d704b221b9cc2f7419a359a19e8e81bc64b724796677396`.
The note's terminal `0a` plus the added `0a` form the blank line after it; the
existing two `0a` bytes form the blank line before it. The expected
post-mutation linked-worktree file is 58,477 LF-only bytes with raw SHA-256
`c52301c17ef6babe57fbaa9d71f0828587ccc83cb1b828b5fa9d26551d55ce3b`
and normalized Git blob SHA-1
`485b450af9729bbfed8d3bef1a136384bb3cb47d`.

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
- Direct installed-definition reproduction against handler `a04cf380...`
  executed the exact installed `commandWindows` and an otherwise identical
  command with only `-X utf8=1` added. Each row used identical canonical JSON
  payload bytes in both modes; every process exited 0. `allow` means empty
  stdout/stderr, and `deny` means the generic runtime-integrity denial:

  | Witness | UTF-8 | Payload bytes | Payload SHA-256 | Locale | UTF-8 |
  |---|---|---:|---|---|---|
  | ASCII | `70 6c 61 69 6e` | 99 | `cd510e10422c86fc10ad577ff3cbe55dd37c2a143fb4fc672848a2bb97743f69` | allow | allow |
  | U+0081 | `c2 81` | 96 | `719d96b8c7c818e315eeab07f7bbae6840eb9853878b74052df491db5e0c3231` | deny | allow |
  | U+008D | `c2 8d` | 96 | `dc7330c23dd44507905d4101a4dda38193d2404a4849423324bf2bb7387355dc` | deny | allow |
  | U+008F | `c2 8f` | 96 | `d7dc683515483fe556b196d0a6efffa4301ec7f311d2ec62cd3a504e90d24c74` | deny | allow |
  | U+0090 | `c2 90` | 96 | `96ef8ddaf9d0f1077f50df41d8639d2def2f99f62112f0052f255807a70c61b3` | deny | allow |
  | U+009D | `c2 9d` | 96 | `819d266a91ee1b520e90dbce65c7119b24376c6fdd2e988d9ee854cef191b810` | deny | allow |
  | U+0401 | `d0 81` | 96 | `3d94ad6a575374826065c34e5d1ebd54f75ed0eeb331fe2a0b2769f49e3a86f7` | deny | allow |
  | U+044D | `d1 8d` | 96 | `ac71e190b29b2580364d04f3963f509c8993397833a7fc786e248f7058e84290` | deny | allow |
  | U+4E0D | `e4 b8 8d` | 97 | `d15768f98eea1f1d088d28a14fca39b3361d3aded0b0ed165a9ab73612487662` | deny | allow |
  | U+1F50D | `f0 9f 94 8d` | 98 | `dfe99c08b0d9154c43e44d9e6cc57b2076b3bcf2efa718d1064678c5ced9df00` | deny | allow |
  | U+1F601 | `f0 9f 98 81` | 98 | `8293a4e0ee5ab2bb0dac97098c706d1f07199dc47ec90891eedfef66a44be2c6` | deny | allow |
  | em dash | `e2 80 94` | 97 | `544110551e5ec177016d7da5fd92830efd068c18b69d7d75b81bd4e62b863eee` | allow | allow |

  Locale denials had stdout SHA-256
  `0293c394b87974cfcf244b0c609689c78854c1579d014c76b4c5691dbafce315`;
  allowed stdout and every stderr were empty
  (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
  Runtime SHA-256 before and after remained
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
- `git config --show-origin --get core.autocrlf` reports exact system origin
  `C:/Program Files/Git/etc/gitconfig` and value `true`; it is not a key in
  `common/config`. The worker/control Git environment nulls system and global
  config, while the committed `eol=lf` attribute remains authoritative.
- `scripts/check_sync.py` has an explicit 11-entry `PAIRS` list and does not
  include `docs/AI_OPERATOR_GUIDE.md`; the guide is neither a sync mirror nor a
  generated packet artifact. A one-file guide mutation therefore does not
  conflict with the sync gate.
- The Owner checkout's clean on-disk guide preimage is a mixed-EOL
  representation (56,878 bytes, raw SHA-256
  `8304f1a1f16c7b42245a7456073b5410acc8fb161ff24f7ae6a3078602b1adf7`)
  of the same normalized blob. Worker acceptance uses the LF-only linked
  worktree commitment above. Integration acceptance separately requires the
  exact inserted block and the expected normalized blob; it does not
  misdescribe pre-existing working-tree EOL representation as mutation drift.
- The prior rebased preimage `cba39073...7bb` is stale because later reviewed
  orchestration-efficiency hardening changed the guide after the unchanged
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
  review cycle. The hard wrapping is the peer-corrected frozen artifact, not
  transport reflow. Packet evidence records that disposition and leaves any
  later relocation to a separately governed follow-up.
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

The current recovery uses one compact `claude-opus-5` planning critique with
`review_kind=plan`, `effort=medium`, a 500-second timeout, a $1.50
provider-reported ceiling, and no automatic second round. A schema-valid
non-converged result, transport failure, model mismatch, malformed output, or
budget refusal stops before mutation. The post-mutation peer call is separate:
one compact exact-diff critique with `review_kind=implementation`,
`effort=medium`, the same per-call timeout and ceiling, and no automatic retry.
These are independent required gates, not two rounds of the same phase.

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
The same preflight invokes exact current executable
`C:\Users\Daniel Paez\AppData\Local\OpenAI\Codex\bin\69066b736e1e17a4\codex.exe`
with argument `--version` and requires exact output
`codex-cli 0.146.0-alpha.3.1`. A missing, changed, or nonzero result stops
before mutation.

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
push invocation uses `-F NUL`, so ambient `Host`, `Match`, `SetEnv`, and
`LocalCommand` directives are not loaded, and pins `BatchMode=yes`,
`HostName=github.com`, `User=git`, `Port=22`, `ProxyCommand=none`,
`ProxyJump=none`, `ControlMaster=no`, `ControlPath=none`,
`PermitLocalCommand=no`, `RemoteCommand=none`,
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
   `a04cf380...`, exact Codex CLI version output, the resolved hook interpreter
   path/version/encoding above, and a same-buffer SHA-256 recheck of committed
   `sdd-plus/changes/codex-host-mvp/integrated-dogfood-note.txt` against
   `5bd5e43b...a69cd`. The worker reads that exact committed note copy from its
   linked worktree. Preflight also records
   `git check-attr text eol -- docs/AI_OPERATOR_GUIDE.md`, the complete Git
   config allow-list result, and the sanitized effective push URL/SSH
   destination. The exact clean HEAD after plan evidence is recorded as the
   sole worktree `base_commit`.
   Immediately before worktree creation, Codex asserts
   `git rev-parse <base_commit>:docs/AI_OPERATOR_GUIDE.md` equals
   `26d659a4e654a02ec9be5cb96f0ddcc750cb6235`, recomputes the unique
   `Readiness may call` anchor at byte offset 12,413, and independently
   re-derives the registered 58,477-byte postimage and both hashes. Any
   mismatch aborts to a fresh plan round; values are never recomputed into a
   new mid-run contract.
3. The mutation runner reports the Owner checkout and Git control fingerprints
   unchanged, its lease released, `merged: false`, and exactly the allowed
   documentation file changed.
4. Codex inspects the full diff against this plan, compares both the raw
   linked-worktree file SHA-256 against `c52301c1...` and the normalized Git blob
   produced by `git hash-object --path docs/AI_OPERATOR_GUIDE.md` against
   `485b450...`, and confirms no claim exceeds the reproduced mechanism. Any
   mismatch aborts rather than being waived as line-ending noise.
5. Claude cross-reviews the exact diff as untrusted data, receiving the
   inserted note text plus both adjacent paragraphs, and reports no semantic,
   placement, or claim-calibration blocker. The peer is not asked to attest
   transport bytes or recompute a digest. Codex alone extracts the exact note
   byte sequence placed in the cross-review input, records its byte count and
   SHA-256, and requires equality with the frozen 1,847-byte artifact and
   `5bd5e43b...a69cd`; a transport delta is a blocker, not a peer waiver. A
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
   there that the 1,848-byte insertion, normalized Git blob, executable
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
   Codex invoke the official admitted `process_runner.py integrate` path. That
   wrapper consumes the integration admission, repeats its preconditions, and
   runs pinned Git `merge --ff-only --no-edit --no-stat --no-verify
   <candidate_commit>` with `merge.autoStash=false`; it does not use
   `update-ref`. Because the changed guide is materialized under committed
   `eol=lf`, the expected Owner working-tree file after the fast-forward is the
   same 58,477 LF bytes and raw SHA-256 `c52301c1...` as the candidate
   worktree. Any stale index/worktree, CRLF rewrite, or other raw-byte mismatch
   blocks. It then
   requires the actual Owner `HEAD`, normalized Git blob `485b450...`,
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
    by the exact 58,477-byte postimage gate. It keeps release, archive, merge,
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
paragraph to the 1,847-byte frozen note; the first and third paragraphs are the
unique adjacent committed guide context. The peer does not attest transport
bytes or repository digests.

```text
The current `model` and `permission_mode` evidence comes from the fresh
PreToolUse activity record. The older SessionStart record remains only the
packet-fingerprint baseline and is not presented as current model/permission
context.

Known tested-host limitation (Codex CLI `0.146.0-alpha.3.1`, Windows 11
Pro `10.0.26200` build `26200`, Python `3.14.0`, locale encoding
`cp1252`): the current `py -3 -I -S` inline verifier reads hook stdin
through the interpreter's locale-decoded text stream before re-encoding it
as UTF-8 for the verified runtime. On this host, cp1252 cannot decode input
bytes `81`, `8d`, `8f`, `90`, or `9d`; any UTF-8 payload containing one of
those bytes fails before the verified runtime evaluates policy and is denied
under the generic runtime-integrity message. Matched installed-definition
probes denied witnesses for all five bytes only in locale mode and allowed
them with the otherwise identical `-X utf8=1` verifier. The same A/B result
held for ordinary UTF-8 examples from Cyrillic (U+0401, bytes `d0 81`, and
U+044D, bytes `d1 8d`), CJK (U+4E0D, bytes `e4 b8 8d`), and emoji (U+1F50D,
bytes `f0 9f 94 8d`, and U+1F601, bytes `f0 9f 98 81`). These witnesses show
that the availability failure is not limited to obscure control codepoints;
they do not establish that every non-ASCII payload is denied. ASCII and an
em-dash payload were allowed in both modes, but static byte-flow inspection
confirms the accepted em-dash bytes are transformed by the cp1252 decode and
UTF-8 re-encode before policy evaluation. The current policy patterns are
ASCII and no decision flip was reproduced, which is not proof that every
non-ASCII decision is unaffected; any future non-ASCII policy pattern would
be evaluated against transformed text until this is fixed. The undefined-byte
cases failed closed and created no false green, but the displayed integrity
reason did not establish an integrity failure: the observed cause was payload
decoding. Explicit UTF-8 byte decoding and separate decode/parse versus
integrity failure reasons remain tracked follow-ups.

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
