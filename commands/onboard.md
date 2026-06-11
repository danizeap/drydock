---
description: Guided first change - learn Drydock by shipping one real thing
---
Run the Drydock onboarding: teach by doing one small, real change end to end. Audience: someone who has read nothing. Keep every step short, explain *why* before *how*, one step at a time, and wait for the Owner where input is needed.

1. **Orient (1 minute).** Explain the core idea in plain words: specs are the source of truth; every meaningful change lives in a packet; safety rules block dangerous moves automatically; nothing ships unverified. Promise: the whole tour is one small change.
2. **Context.** If `PROJECT_CONTEXT.md` is missing or template-y, run the context interview now (what are we building, for whom, what does done mean, stack, constraints). Write the file.
3. **Pick the change.** Ask the Owner for a genuinely small improvement they actually want (a fix, a small feature, a tweak). If they have nothing, propose one from the codebase. Keep it LITE/STANDARD sized.
4. **Open the packet.** Run `/drydock:new` flow: create the change, fill brief and plan from the conversation, declare mode and primary skill out loud so the Owner sees the routing happen.
5. **Delta spec (if behavior changes).** Write one or two SHALL requirements with WHEN/THEN scenarios. Show the Owner: "this is what the system will promise after the change."
6. **Implement** under the declared skill's rules. Narrate the moments where Drydock constrains you (existing pattern followed, test intent stated, no opportunistic refactor) — that's the product working.
7. **Verify.** Run `/drydock:verify`: script checks, spec coverage, the verifier subagent. Show the Owner the three-dimension report.
8. **Archive.** Run `/drydock:archive` through the gates: sync the delta spec into the living capability spec and point at the updated file — "your documentation just updated itself."
9. **Close the loop.** Recap what now exists (packet in archive, living spec, tests), name the three commands they'll use daily (`/drydock:new`, `/drydock:verify`, `/drydock:archive`), and mention `/drydock:explore` for thinking and the hooks quietly protecting them. Invite them to file friction at the repo's issues.
