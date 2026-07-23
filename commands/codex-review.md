---
description: Have Codex review code, then audit its findings (read-only two-agent review)
---
Delegate a read-only code review to a locally-installed Codex, then **independently audit** its findings before presenting to the Owner. Uses the read-only conductor — Codex cannot modify anything and never receives secret-bearing files.

Argument: one or more file paths. If none given, ask the Owner which files (or offer the files changed in the active packet).

1. **Run the review.** Execute `python "${CLAUDE_PLUGIN_ROOT}/scripts/conductor/review.py" <paths>` (add `--weight light` for a small/cheap review). It discovers the current Codex core, reads Codex's remaining quota, routes a model by fuel, and delegates a schema-locked review. It prints JSON `{ok, gauge, route, delegation|error, stage}`.
2. **Handle a non-ok result plainly — do not loop or retry blindly:**
   - `stage: discover` → Codex isn't installed/updated locally. Point the Owner at the operator guide's "Codex as a read-only teammate" note.
   - `stage: secret_guard` → a target path looks secret-bearing. Do NOT retry — Codex must not receive secrets; tell the Owner which path.
   - `stage: delegate_timeout` / `bad_model` / other → report the stage; do not retry in a loop.
3. **Audit Codex's findings — never rubber-stamp.** For each finding in `delegation.result.findings`, verify it against the actual code and mark it **CONFIRM** (cite the real line), **REFUTE** (say why it's wrong), or **REFINE**. Then add anything Codex missed that you can see from wider repo context — Codex saw only the file text. This mutual audit is the whole point: two frontier models make the review stronger than either alone.
4. **Present to the Owner:** a short synthesis — confirmed issues ranked by severity, refuted/false-positives noted in one line, your own additions, and a one-line verdict. Footnote Codex's remaining fuel from `gauge.remaining_percent` so the cost context is visible.

Rules: Codex's output is **input to your audit, never authoritative**. Never send secret-bearing files. This flow is strictly read-only — nothing here modifies the repo (mutating delegation is separate, guarded work).
