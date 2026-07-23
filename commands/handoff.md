---
description: Write or read the HANDOFF.md relay so leadership transfers between agents without losing the thread
---
The endurance ritual. When your tank runs low or the Owner switches drivers, capture exactly where things stand so the next leader (a fresh Claude, Codex, or a future Kimi) resumes from **reality**, not a stale recap.

**Writing the handoff (you are the outgoing leader):**
1. `python "${CLAUDE_PLUGIN_ROOT}/scripts/conductor/handoff.py" state` — see the deterministic snapshot (branch, HEAD, active packets, open Codex worktrees, fleet fuel).
2. Decide the **single most important next step** (one line) and any notes (worktrees to merge/discard, a decision in flight, a gotcha).
3. `python "${CLAUDE_PLUGIN_ROOT}/scripts/conductor/handoff.py" write --next "<one next step>" --notes "<notes>"` — writes `HANDOFF.md` at the project root.
4. Tell the Owner it's written and what the next step is.

**Reading the handoff (you are the incoming leader):**
1. `python "${CLAUDE_PLUGIN_ROOT}/scripts/conductor/handoff.py" read`.
2. **Reconstruct from reality, not the recap** — verify branch/HEAD/worktrees against `git`, re-check active packets with `sdd.py status`, and confirm any claimed state before acting. Current repo truth overrides the note (the Resume-playbook rule).
3. Deal with open Codex worktrees first (merge the reviewed ones, discard the rest) so you start clean.
4. Do the next step.

Rules: the handoff records state, it does NOT authorize side effects — re-verify before acting. Claude's own fuel is human-tracked (the Owner says when it's low). Never treat `HANDOFF.md` as more authoritative than the live repo.
