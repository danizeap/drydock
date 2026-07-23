# Brief

## Change

codex-review-diff — `/drydock:codex-review --diff`: auto-discover the files you just changed and review them, so cross-model review becomes a natural pre-`verify` step instead of hand-picking paths. Plus the seven defects Codex found when the feature was pointed at its own implementation.

Intake: Mode STANDARD, with a `verifier` pass because auto-discovery widens what gets *sent off-machine* (a security-relevant change of posture). Primary skill: `backend`. Approvals: Owner directed it after the field report named this "the single highest-frequency use". Stop conditions: any path where auto-discovery sends secret material or reads outside the repository; any silent skip.

## What this means for your product

`codex-review --diff` reviews what you just changed — working tree vs HEAD (including untracked files), or a whole branch with `--base main`. Run it right before `/drydock:verify`. Anything it refuses to send (secret-bearing by name **or by content**, or a symlink pointing outside the repo) is reported, never silently dropped.

## User Need

From the field report: *"Today I hand-picked files. The single highest-frequency use is 'review what I just changed in this packet before I call it done.'"* Hand-picking is friction at exactly the moment the review is most valuable, and it means the reviewer sees what you remembered rather than what you actually touched.

## Scope

In scope:
- `changed_files(base)` — NUL-delimited (`-z`) git listing of changed + untracked files, **plus deleted paths**, returning a real **error** rather than an empty set when git fails.
- `review.py --diff [--base <ref>]`; explicit paths still supported.
- **Auto-discovery guards (the security half):** secret-bearing paths are *skipped and disclosed* rather than failing the run (an explicit path is still refused); a **content-level** secret scan catches keys embedded in innocently-named files; auto-discovered paths must resolve **inside the repo** (a changed symlink must not read out-of-tree).
- Prompt hardening: an escalating boundary marker the reviewed content cannot close.
- All-JSON contract honoured on argparse failure.
- Command doc leads with `--diff` as the pre-`verify` step and names every non-ok stage.

Out of scope: sending diff hunks (full content is deliberate — see decision log); per-packet change sets (Drydock does not track them); 6.3 (`mutate --files` scope hint) — next packet.

## Acceptance Criteria

- [ ] `--diff` finds modified + untracked files, reports deleted paths, and skips binaries/generated files.
- [ ] A git failure (e.g. bad `--base`) is an error, never "no changes".
- [ ] Auto-discovery never sends: a secret-named file, a file whose **content** looks like secret material, or a symlink resolving outside the repo — each skipped and reported.
- [ ] An explicitly named secret path (by name or content) is still refused outright.
- [ ] File content cannot close the prompt's boundary marker.
- [ ] Every outcome is structured JSON, including argument errors. Full suite green.

## Impact Areas

- Backend: `review.py` (discovery + guards + prompt), `commands/codex-review.md`.
- API: `changed_files()` returns `(files, deleted, error)`; result gains `reviewed`, `deleted`, `skipped_secret`, `skipped_outside_repo`; new stages `git_error`, `no_changes`, `only_deletions`, `nothing_to_review`, `secret_content`, `bad_arguments`.
- Operations/security: auto-discovery widens the send surface — offset by content scanning and repo containment.
- Documentation: command doc; capability spec.

## Open Questions

- Should `--diff` optionally include diff hunks alongside full content for very large change sets? (Deferred; the size caps currently push the operator to narrow the set instead.)
