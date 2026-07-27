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

Intended files:

- `delegation_contracts.py` owns immutable boundary types, bounds, safe
  identifiers/references, canonical JSON, and content-minimal persistence.
- `delegation_ledger.py` owns one run's serialized event file and honest
  integrity report.
- `capability_profiles.py` owns pure shadow reduction and the optimistic
  controller-asserted verified-terminal profile commit log. It explicitly does
  not establish evidence provenance or verifier independence.
- Three focused test modules own the contract, corruption, concurrency,
  replay, conflict, and gate proofs.
- This packet owns decisions and evidence; existing live orchestrator and
  process-runner paths remain unchanged.

Design choice: keep contract validation, run-event storage, and capability
reduction separate so future provider adapters cannot couple raw provider
content to long-lived evidence. Use local append-only JSONL and stdlib OS locks
because the project has no runtime dependency layer and the data is
single-Owner operational evidence, not a multi-tenant database.

Risks before coding:

- a permissive identifier could escape a state root;
- concurrent writers could allocate duplicate sequences or interleave bytes;
- partial usage could be promoted to an invented total;
- a modified stream could be extended and laundered as valid;
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
2. Add a local append-only run ledger whose single-record append holds a
   bounded cross-platform file lock, verifies the existing chain, and fsyncs
   the new record before success.
3. Store only digests, identifiers, bounded status metadata, sanitized errors,
   evidence references, and normalized usage.
4. Add a pure shadow reducer. It copies a frozen profile snapshot, rejects
   duplicate observations, detaches caller-owned collections, retains immutable
   source contracts, and updates only observable counts and aggregates.
5. Add an append-only profile commit store. A commit requires an unchanged
   start digest, a unique observation set, terminal status `verified`, and a
   relative verification reference. The live controller, not this store,
   remains responsible for establishing the evidence result and provenance.
   The store recomputes the exact aggregate snapshot from the source contracts
   before appending.
6. Test schema rejection, secret-shaped data, corruption, hash reordering,
   duplicate replay, frozen-state preservation, concurrent append, optimistic
   conflict, and failed/unverified commit refusal.
7. Leave executor integration, routing policy, UI, Claude telemetry, and real
   model calls to later bounded packets.

## Files Expected To Change

- `adapters/codex/drydock/scripts/delegation_contracts.py`
- `adapters/codex/drydock/scripts/delegation_ledger.py`
- `adapters/codex/drydock/scripts/capability_profiles.py`
- `adapters/codex/tests/test_delegation_contracts.py`
- `adapters/codex/tests/test_delegation_ledger.py`
- `adapters/codex/tests/test_capability_profiles.py`
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
packet. Rollback is removal of the modules, tests, and packet before any
consumer depends on them. Persisted test fixtures live only in temporary
directories.
