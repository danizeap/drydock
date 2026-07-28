# Plan

## Change

adaptive-delegation-ledger

## Backend Change Plan

Classification: local data mutation and server-side agent orchestration
substrate.

Existing pattern found: Codex adapter runtime modules use the Python standard
library, validate subprocess/provider boundaries explicitly, reject duplicate
JSON keys and non-finite values, write local state with flush/fsync, and prove
behavior in `adapters/codex/tests/`. This packet follows that shape without
adding a dependency, network call, command launcher, or global mutable
business state.

Schema-v2 remediation keeps that architecture: a bounded structural-prefix
scanner classifies only incomplete terminal JSON; complete observed records
must match their canonical serialization byte-for-byte, including LF. Repair
intents are not trusted as isolated documents: each one must describe bytes
reachable from the locked current ledger. A repair candidate is the exact
valid prefix plus one canonical reserved in-chain `drydock_repair` marker, so
the repaired ledger cannot be confused with a pristine prefix.

Intended files:

- `delegation_contracts.py` owns immutable boundary types, bounds, safe
  identifiers/references, canonical JSON, and content-minimal persistence.
- `delegation_ledger.py` owns one run's serialized event file and honest
  integrity report.
- `capability_profiles.py` owns pure shadow reduction and the optimistic
  unauthenticated controller-asserted `passed` profile commit log. Its
  `controller_asserted_status` and `asserted_verification_ref` fields do not
  establish evidence existence/origin, a pass result, verifier independence,
  permission, or authority.
- Four focused test modules own the contract, corruption, concurrency,
  replay, conflict, and gate proofs.
- `scaffold_bundle.py`, its focused test, and the generated bundle own the
  independent fresh-checkout LF prerequisite exposed by this worktree.
- This packet owns decisions and evidence; existing live orchestrator and
  process-runner paths remain unchanged.

Design choice: keep contract validation, run-event storage, and capability
reduction separate so future provider adapters cannot couple raw provider
content to long-lived evidence. Use local append-only JSONL and stdlib OS locks
because the project has no runtime dependency layer and the data is
single-Owner operational evidence, not a multi-tenant database.

The implemented lock is a sidecar file initialized with one NUL at byte zero.
Writers use binary `a+b`; existing-file read-only calls use binary `r+b` on
both OS paths without writing, then `seek(0)`. Windows uses custom nonblocking
`msvcrt.LK_NBLCK` for the one-byte range at offset zero; POSIX uses
`fcntl.flock(..., LOCK_EX | LOCK_NB)` for the sidecar file (the seek does not
turn POSIX flock into a byte-range lock). Attempts retry every 25 ms against
the caller's monotonic timeout, whose hard maximum is 30 seconds. First-open
initialization occurs only after the selected OS lock is acquired, so racing
opens cannot append initialization bytes. Handle close or process crash
releases the OS lock; there is no PID file, stale-lock reaper, or claim that
the two OS primitives are semantically identical beyond the tested
serialization behavior.

Risks before coding:

- a permissive identifier could escape a state root;
- concurrent writers could allocate duplicate sequences or interleave bytes;
- partial usage could be promoted to an invented total;
- a modified stream could be extended and laundered as valid;
- semantically equivalent whitespace, CRLF, key order, or escaping could hide
  byte mutation unless replay compares exact canonical bytes;
- a syntactically valid repair intent could describe an impossible candidate
  or missing/conflicting quarantine;
- learning could update mid-run, replay an observation, overwrite a newer
  state, or be mistaken for authority;
- logs could retain prompts, repository content, provider bodies, or secrets;
- an unkeyed local hash chain could be overstated as authentication.

Stop conditions:

- any learned value authorizes an effect, waives a gate, establishes
  convergence, or replaces Owner judgment;
- identifiers/references cannot be proven path-safe;
- concurrent append cannot be serialized on Windows and POSIX;
- corrupted state can still be extended;
- raw model/repository content or credentials are required for persistence;
- Claude-dependent peer review is silently replaced with implementer review.

Ownership map:

| Data touched | Owner | Access rule | Where enforced |
| --- | --- | --- | --- |
| Local delegation metadata, digests, usage counts, and evidence references | Repository Owner | Drydock controller may append bounded sanitized records; no provider or remote access is added | Strict contracts plus ledger/profile append boundaries |
| Raw prompts, repository/file contents, provider bodies, credentials, account identifiers | Repository Owner / provider account holder | Must not enter persistent delegation evidence | Exact schemas, forbidden persisted fields, size/secret checks, negative tests |

Note: the architecture blueprint and delta spec preceded runtime code. This
skill-specific compact plan was added when `backend` was selected as a
supporting implementation skill, before broad verification and integration.

## Approach

1. Freeze strict stdlib-only contracts for delegation envelopes, results,
   outcome observations, and capability profiles.
   Envelopes persist a request-binding digest; results separate trusted runtime
   status from untrusted claimed terminal/error detail.
2. Add a local append-only run ledger whose single-record append holds a
   bounded cross-platform file lock, verifies the existing chain, and fsyncs
   the new record before success.
3. Store only digests, identifiers, bounded status metadata, sanitized errors,
   evidence references, and normalized usage.
4. Add a pure shadow reducer. It copies a frozen profile snapshot, rejects
   duplicate observations, detaches caller-owned collections, retains immutable
   source contracts, and updates only observable counts and aggregates.
5. Add an append-only profile commit store. A commit requires an unchanged
   start digest, a unique observation set,
   `controller_asserted_status="passed"`, and an
   `asserted_verification_ref`. Both are unauthenticated controller
   assertions. The live controller, not this store, remains responsible for
   establishing evidence existence, origin, actual pass result, and verifier
   independence.
   The store recomputes the exact aggregate snapshot from the source contracts
   before appending.
   Persist every full source triple and its typed reduction decision. Enforce
   32 commits and 64 source submissions per commit.
6. Require exact canonical serialization plus LF when replaying ledger events
   and profile commits; otherwise verification is corrupt and mutation stops.
7. Validate every repair intent against the current before, prepared candidate,
   completed candidate, or exact later-appended stream. Recompute the exact
   reserved marker and the prefix-plus-marker candidate, including
   length/digest/record count/final digest, and require any selected quarantine
   before completed replay. `verify` exposes repair-history count/presence and
   `read_records` returns the marker; ordinary `append` refuses its event type.
8. Test schema rejection, secret-shaped data, corruption, hash reordering,
   duplicate replay, frozen-state preservation, concurrent append, optimistic
   conflict, fabricated-assertion characterization, and non-`passed` commit
   refusal.
9. Regenerate the scaffold bundle from LF-normalized source and reject CRLF in
   text bundle entries. Treat the old generated bytes as a pre-existing
   fresh-checkout prerequisite, not a ledger regression.
10. Leave executor integration, routing policy, UI, Claude telemetry, and real
   model calls to later bounded packets.

Serialization is frozen to Python's `json.dumps` with `sort_keys=True`,
`separators=(",", ":")`, `ensure_ascii=True`, and `allow_nan=False`. Values
retain the exact Python code-point sequence with no Unicode normalization, so
canonically equivalent Unicode spellings remain distinct. Files are read and
written in binary mode with exactly one LF per accepted record. This is a
Python finite-number contract, not a cross-language canonical-JSON claim.
Caller-supplied timestamps must be real millisecond UTC `...Z` values; default
timestamps use the OS wall clock and are not required to be monotonic.

File data and repair artifacts are flushed and file-fsynced. Directory fsync
is performed after durable metadata transitions on POSIX; Windows has no
equivalent directory-fsync call in this stdlib implementation, so atomic
replace and file fsync do not make an equal power-loss durability claim.

## Files Expected To Change

- `adapters/codex/drydock/scripts/delegation_contracts.py`
- `adapters/codex/drydock/scripts/delegation_ledger.py`
- `adapters/codex/drydock/scripts/capability_profiles.py`
- `adapters/codex/tests/test_delegation_contracts.py`
- `adapters/codex/tests/test_delegation_ledger.py`
- `adapters/codex/tests/test_capability_profiles.py`
- `adapters/codex/tests/test_delegation_integration.py`
- `adapters/codex/drydock/scripts/scaffold_bundle.py`
- `adapters/codex/tests/test_scaffold_bundle.py`
- `adapters/codex/drydock/assets/project-scaffold.bundle.json`
- this change packet and its delta spec

## Risks

- A hash chain can be mistaken for authentication unless limitations are
  returned with every verification.
- Local model names and task classes can create unbounded cardinality; fields
  and snapshot size require hard limits.
- A future scheduler can overfit small samples; this packet stores evidence but
  deliberately does not choose a scoring algorithm.
- Error summaries and evidence references can carry sensitive text unless
  bounded validation rejects known secret shapes and forbidden fields.
- Concurrent controllers can race; append and profile commits require a
  process-level file lock on Windows and POSIX.
- Profile learning can become governance authority through later misuse; the
  non-authoritative boundary is normative and tested at the contract surface.

## Rollback

The new modules are additive and are not wired into live delegation in this
packet. Before any consumer depends on them, runtime/test changes can be
reverted deliberately. The generated project-scaffold bundle is a consumed
plugin artifact and must not simply be deleted: rollback rebuilds it from the
intended reverted `assets/project-scaffold` source and reruns its check.
Persisted test fixtures live only in temporary directories; schema v2 has no
live compatibility obligation.

## Verification Environments

Local commands and CI evidence are separate. Local focused commands use the
available Python interpreter and are recorded in `verification.md`. Existing
`.github/workflows/ci.yml` already runs both `tests/` and
`adapters/codex/tests/` on `ubuntu-latest` and `windows-latest` with Python 3.9
and 3.12. No redundant workflow is added. The repository-wide
`.gitattributes` rule `* text=auto eol=lf` already covers source and generated
bundle text, so this packet documents that coverage rather than duplicating it.
