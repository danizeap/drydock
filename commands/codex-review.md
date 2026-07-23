---
description: Have Codex review code, then audit its findings (read-only two-agent review)
---
Delegate a read-only code review to a locally-installed Codex, then **independently audit** its findings before presenting to the Owner. Uses the read-only conductor — Codex cannot modify anything and never receives secret-bearing files.

Argument: one or more file paths — or nothing, to review **what you just changed**.

1. **Run the review.**
   - **Most common — review your current work (the natural step right before `/drydock:verify`):** `python "${CLAUDE_PLUGIN_ROOT}/scripts/conductor/review.py" --diff` — the working tree vs HEAD, including untracked files. Add `--base main` to review a whole branch instead.
   - **Specific files:** `… review.py <paths>`. Add `--weight light` for a small/cheap review.

   It discovers the current Codex core, reads remaining quota, routes a model by fuel, and delegates a schema-locked review. Prints JSON `{ok, gauge, route, reviewed, deleted, skipped_*, delegation|error, stage}`. Paths that resolve inside the repo are reported repo-relative; an explicitly named file outside the repo is reported as given.
2. **Handle a non-ok result plainly — do not loop or retry blindly:**
   - `stage: bad_arguments` → the invocation was refused rather than silently narrowed. This includes `--diff` given *with* paths, and `--base` given *without* `--diff` — in both cases scope you asked for would have been ignored. Re-run with one or the other. An option-shaped `--base` (e.g. `--output=…`) is refused here too, before git ever sees it.
   - `stage: discover` → Codex isn't installed/updated locally. Point the Owner at the operator guide's "Codex as a read-only teammate" note.
   - `stage: secret_guard` → an **explicitly named** path looks secret-bearing. Do NOT retry — Codex must not receive secrets; tell the Owner which path.
   - `stage: no_changes` → nothing reviewable changed; say so rather than inventing files to review.
   - `stage: git_error` → the git query failed (e.g. a bad `--base`). Report it — this is NOT "your branch is clean".
   - `stage: only_deletions` → the change only removes files; there is nothing to read. Say what was deleted.
   - `stage: nothing_to_review` → everything was filtered by the guards; nothing was sent. Report why from `skipped_secret` / `skipped_outside_repo`.
   - `stage: secret_content` → an explicitly named file *contains* secret material (the name looked innocent). Do NOT retry.
   - `stage: no_repo_root` → repository containment could not be established, so **nothing was sent** (fail-closed). Report it; don't work around it by naming paths explicitly.
   - **Surface the skip lists on every result — including failures.** `skipped_secret` (secret by name or content), `skipped_outside_repo` (resolves outside the repo), `skipped_missing` (vanished between discovery and read), `skipped_not_reviewable` (binary/generated), and `deleted` are present on *every* outcome, not just successes: a run that ended in `too_large` may still have declined to send a `.env`, and the Owner needs to know that. Deletions are reviewable changes whose content could not be read — note that a **secret-bearing deleted path is named to the Owner but withheld from the reviewer**, so `deleted` and what Codex saw can legitimately differ.
   - `stage: delegate_timeout` / `bad_model` / other → report the stage; do not retry in a loop.
3. **Audit Codex's findings — never rubber-stamp.** For each finding in `delegation.result.findings`, verify it against the actual code and mark it **CONFIRM** (cite the real line), **REFUTE** (say why it's wrong), or **REFINE**. Then add anything Codex missed that you can see from wider repo context — Codex saw only the file text. This mutual audit is the whole point: two frontier models make the review stronger than either alone.
4. **Present to the Owner:** a short synthesis — confirmed issues ranked by severity, refuted/false-positives noted in one line, your own additions, and a one-line verdict. Footnote Codex's remaining fuel from `gauge.remaining_percent` so the cost context is visible.

Rules: Codex's output is **input to your audit, never authoritative**. Never send secret-bearing files. This flow is strictly read-only — nothing here modifies the repo (mutating delegation is separate, guarded work).
