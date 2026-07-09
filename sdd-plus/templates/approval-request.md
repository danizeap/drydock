# Approval Request Template

Copy the form that fits and fill it in the Owner's own language. The header line
`APPROVAL NEEDED` is a stable marker — keep it exactly. Governed by
`sdd-plus/protocols/framework-usage.md` §7.

Use the **FULL** form for side effects and gate overrides (destructive migrations,
data deletion, deploys, payments, permission/role changes, sending external
messages, breaking APIs, production secret/config changes, irreversible external
actions, CLASS 3–4 tool capabilities, disabling a guardrail).

Use the **QUICK** form for routine process/plan choices (e.g. archiving with
unsynced specs, choosing an execution mode).

---

## FULL form

```text
APPROVAL NEEDED — [CANNOT BE UNDONE | UNDO UNCERTAIN | undoable]
What I want to do: <one sentence, in names the Owner recognizes — "the customer table", not "destructive migration">
Why I'm asking you: <plain risk category — "this deletes data" / "this emails real people" / "this changes who can see what">
What could go wrong: <worst realistic case, concrete — "all ~1,240 customer rows would be gone">
Who/what is affected: <just this project's code | your data | people outside (emails sent, money moved, live site)>
Undo: <exactly one of: a concrete procedure named in the plan | NOT REVERSIBLE | REVERSIBILITY UNKNOWN>
Safety net after your yes: <which guardrails still apply | "none — past this point nothing automatic catches a mistake">
Your options: approve  ·  approve <numbers> (only those parts)  ·  no  ·  ask anything (a question is never a yes)
```

Rules for the FULL form:

- **Undo is a closed choice.** Write one of the three values verbatim. Never invent a
  fourth or free-text a reassurance — a hallucinated "easy to undo" for a destructive
  action is worse than no frame, because the frame vouches for it.
- **Plain referents only.** Name the thing the Owner recognizes, never the risk-class
  jargon ("the sign-up emails", not "the transactional email side-effect").
- **Severity in the header matches the Undo line.** `CANNOT BE UNDONE` when Undo is
  `NOT REVERSIBLE`; `UNDO UNCERTAIN` when Undo is `REVERSIBILITY UNKNOWN`; `undoable` only
  when Undo names a concrete procedure. Never show an unknown reversibility as `undoable`.
- **Multiple actions get numbered.** If the ask bundles more than one distinct action, make
  "What I want to do" a short numbered list (split anything past ~4 into separate asks) so the
  Owner can `approve 1, 3`.

## QUICK form

```text
APPROVAL NEEDED (routine)
What: <one sentence>
Why you: <the one thing being decided>
approve or no
```

---

## After the Owner responds

- **approve** / **approve 1, 3** — restate what was approved in one line, then do exactly
  that, once ("Approved: deleting the staging table. Doing it now."). Unapproved numbered
  parts are declined-for-now.
- **no** — write `OWNER DECLINED: <action> — <date> — Owner: "<verbatim>"` to the packet's
  `decision-log.md`. The action becomes a stop condition; never work around it. Offer at most
  two alternatives, once. Never re-present the identical ask this session.
- **a question / a conditional ("yes, but back up first")** — nothing is approved. Answer the
  question or satisfy the condition, then re-present the same ask once.
- An approval covers only the stated action, once, in this packet. It does not survive the
  session and does not generalize to similar actions.
