---
description: Owner brief - plain-language project status from deterministic facts
---
Render the Owner brief. Topic/args (optional): $ARGUMENTS

Engine: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief.py"` (on Windows: `python`). It is plugin-only — never look for a project copy. It prints a FACTS block (JSON) and always exits 0.

Rendering rules — these are the product, follow them exactly:
1. **Translate ONLY the FACTS block** into plain language, in the Owner's own language. You may not add facts, states, counts, or reassurance the block does not assert. A `goal` field is a goal — never present it as an achieved outcome.
2. **Absence is absence.** `"unavailable"` renders as "I can't see X on this computer" — never as zero, never as fine, never omitted. If `drydock` is `"error"`, say the engine failed and fall back to `/drydock:status`, disclosing the fallback.
3. If `drydock` is `"not-initialized"`: say, in one sentence, that this repo is not set up with Drydock and point at `/drydock:init-project`. Do NOT write OWNER_STATUS.md.
4. Keep framework vocabulary off the surface: no "packet", "delta spec", "LITE/STANDARD/FULL", "BLOCKED", "NOT VERIFIED", or skill names. Use the rung captions' framing ("what you can safely say").
5. Every item ends in either "nothing needed from you" or "your move:" with exactly one decision. Prevention counts are recoverable governed pauses — never danger counts; keep the honest false-alarm clause.
6. After rendering in chat, write the durable snapshot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief.py" --write-status` (add `--lang es`/`--lang en` only when the Owner's language differs from the file's recorded one). Report the write. The engine authors the file bytes — never hand-edit OWNER_STATUS.md (the packet guard denies it).
7. **First-ever write only**: ask the Owner one question — commit OWNER_STATUS.md (visible on GitHub; it lags, its header shows the date) or add it to .gitignore (private to this machine). Record their answer by doing it.
8. Authority order when surfaces disagree: live packet files > `sdd.py status` > the orientation block > OWNER_STATUS.md (a snapshot is stale the moment work continues — offer a refresh, never reconcile by hand).
9. Never run this command unprompted. If the orientation context flagged OWNER_STATUS.md as stale, mention staleness only when the Owner asks about status.
