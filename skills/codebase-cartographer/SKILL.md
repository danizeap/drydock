---
name: codebase-cartographer
description: Create and maintain durable repo maps so the agent can understand a codebase efficiently without rereading everything. Use before broad work in an unfamiliar repo (UNKNOWN), to refresh stale maps (KNOWN_BUT_STALE), or after architecture, API, data, integration, or test changes invalidate prior maps. Not needed when the repo is KNOWN_AND_MAPPED and current.
---

# Codebase Cartographer Skill

Answers: can the agent understand this repo from durable maps before rereading everything or changing code? Maps are token-saving infrastructure, not documentation theater — create them only when they will be read again.

## Knowledge states

- `KNOWN_AND_MAPPED` — current maps identify the affected area: load maps and affected files, skip this skill.
- `KNOWN_BUT_STALE` — maps exist but may be outdated: check freshness, update only affected sections.
- `UNKNOWN` — area or conventions unclear: do bounded mapping before changing code.

## Token-saving rules

Map breadth-first: entry points, main modules, and flows before line-level detail. Read directory structures, configs, route tables, and schema files before module internals. Sample representative files instead of reading every sibling. Record findings in maps as you go so nothing must be reread. Stop mapping when the task's affected area is understood — mapping the whole repo is not the goal.

## Map artifacts (create only what will be reused)

A read-first guide (what to read, in what order, what to ignore); an architecture/module map; an API surface map; a data/storage map; an integration map; a test surface map; a risk-area map. Each map states its freshness date and what would invalidate it.

## Blocking rules

BLOCK (do not proceed to implementation skills) if: the affected area cannot be identified after bounded mapping; ownership or source of truth for the affected data/flow is unclear; or the repo's conventions contradict each other and the dominant convention cannot be determined.

## Boundaries

Do not change code under this skill. Do not produce maps nobody will reread. Do not reread the whole repository merely because a task is important.

## Output

Compact evidence: mapping scope, maps created/updated, entry points and main modules found, risk areas, read-first guidance, staleness notes, result, next skill.
