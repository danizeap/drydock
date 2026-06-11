---
name: testing
description: Prove meaningful behavior with appropriate tests. Use for test design, test changes, regression coverage, negative permission tests, verification commands, skipped-test disclosure, and manual verification evidence. The question is always what behavior must be proven and what proves it.
---

# Testing Skill

Answers: what behavior must be proven, and what tests prove it? Tests exist to prove behavior, not to inflate counts. Listing commands is never enough — every test's *intent* is stated in plain English.

## Preflight

State: change type; existing test pattern found; behavior to prove (plain English); risk areas; test level choice and why; intended test files; stop conditions.

## Test level guidance

Unit for pure logic; route/integration for validation, auth, and contracts; service/repository tests for mutations; end-to-end or smoke only for critical user journeys (expensive — use sparingly); manual verification is acceptable evidence when automated testing is impractical, but must be described concretely (what was done, what was observed).

## Risk coverage rules

- Permission logic requires **negative tests**: the wrong user cannot read or mutate the object.
- State-changing operations test the failure path, not just success.
- Webhooks/jobs test duplicate delivery and partial failure.
- Contract changes test the documented error behavior, not just 200s.
- Bug fixes add a regression test that fails without the fix.

## Test quality rules

Tests assert behavior, not implementation details. No tests that cannot fail (assertion-free, always-true, or mocked into meaninglessness). No weakening existing assertions to make a change pass without flagging it. Flaky or skipped tests are disclosed with reasons, never hidden. Shared fixtures don't smuggle in real personal or production data.

## Blocking rules

BLOCK if: meaningful behavior changed with no tests and no justified manual verification; permission logic lacks negative tests without justification; a stated test was not actually run; tests fail (a failing test means BLOCKED, never PASS); assertions were weakened or tests deleted to force a pass; or test intent cannot be explained in plain English.

## Evidence

STANDARD: compact format plus behavior proven (plain English), happy-path and negative tests, commands run with actual results, skipped/flaky disclosure, coverage gaps. FULL adds: per-category breakdown (permission, contract, db, integration, AI/RAG, regression), manual verification detail, Owner Summary.
