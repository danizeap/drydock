---
name: explainer
description: Explain meaningful software changes to the Owner in plain English and technical layers. Use when the Owner asks how something works, after unusually complex implementations, or when a change needs a durable plain-language explanation so the Owner can own the system without reading every line. Distinct from codebase-cartographer, which maps repos for future agent sessions.
---

# Explainer Skill

Answers: can the Owner understand what changed, how it works, where the important logic lives, what could break, and what to read next? This is the ownership-transfer layer — technically honest, never hand-wavy, never condescending.

## Depth levels (choose before explaining)

- **L1 Executive Summary** — what changed, why it matters, what was tested, what could still go wrong.
- **L2 Guided Technical** (default) — main files and functions, execution flow, data flow, decisions, tests, risks, read-first guidance.
- **L3 Deep Walkthrough** — module boundaries, control flow, state, edge cases, error paths, permission checks, tradeoffs. Use when the Owner asks to study the implementation.
- **L4 Line-by-Line** — only on explicit request; expensive and usually less useful than explaining the important logic deeply.

## Required explanation rules

Plain English first, then technical layers. Name exact files and functions — vague descriptions don't transfer ownership. Separate what is certain from what is assumed; flag anything unverified. Explain *why* decisions were made, not just what exists. Always include: read-this-first guidance, what can be safely ignored for now, and the questions the Owner should now be able to answer (a comprehension checkpoint, not a quiz). Never claim something works that wasn't verified; say "untested" plainly.

## Blocking rules

BLOCK (i.e., do not present an explanation as complete) if: the explanation would describe behavior that was not actually inspected or verified; important uncertainty is being smoothed over; or the source material (diff, files) was not actually read.

## Evidence

The explanation itself, plus: depth level used, sources reviewed, what remains untested/unverified, risks/open questions, and handoff to other skills if the explanation surfaced problems.
