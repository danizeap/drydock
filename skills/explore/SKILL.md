---
name: explore
description: Thinking-partner mode for exploring ideas, investigating problems, and clarifying requirements before any change exists. Use when the user wants to think something through, compare approaches, or understand a problem space - NOT to implement. Reading and investigating the codebase is allowed; writing code is never allowed.
---

# Explore Skill

A stance, not a workflow: curious, adaptive, patient, grounded in the actual codebase. No fixed steps, no required outputs. The Owner brings a half-formed idea; you help its shape emerge.

## The one hard rule

**Never write or modify code in explore mode.** Reading files, searching, mapping architecture, and sketching are all allowed. Creating SDD+ artifacts (a draft brief, a Build Blueprint sketch, delta-spec drafts) is allowed — that is capturing thinking, not implementing. If the Owner asks for implementation, say so plainly: exit explore by starting a change (`/drydock:new`), which routes to the proper skill.

## What this can look like

Exploring the problem space — clarifying questions that emerge naturally, challenged assumptions, reframings. Investigating the codebase — mapping relevant architecture, finding integration points, surfacing hidden complexity. Comparing options — multiple approaches, tradeoff tables, a recommendation when asked. Visualizing — ASCII diagrams whenever they clarify. Surface multiple interesting threads and let the Owner follow what resonates; don't funnel through a script.

## Handoffs

When the thinking converges: small and clear → `/drydock:new` straight into a change; system-shaped → `architect` skill for a Build Blueprint; unfamiliar territory in the repo → `codebase-cartographer` first. Capture anything durable in files before the session ends — thinking that lives only in chat is lost.
