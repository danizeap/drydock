# Plan

## Change

gate15-lethal-trifecta

## Approach

Pure spec/standard/template editing, grounded in the CONFIRMED research finding in `sdd-plus/specs/launchguardian-v0.4-gap-research.md`. No code, so no new tests; verification is coherence + dual-copy byte-identity + the verifier.

1. **Framework spec** (`sdd-plus/specs/launchguardian-framework.md` + scaffold twin):
   - Expand the Gate 15 table row to name the lethal-trifecta test and the "regardless of RLS/read-only" clause.
   - Add a `## Gate 15 — the Lethal-Trifecta Test` subsection after the Gate Model section: the three legs (private data / untrusted content / outbound channel), the rule, why standard access controls do not break it (service_role bypasses RLS; read-only still permits read + injection + exfil), the break-a-leg controls (scope data to the requesting user; isolate untrusted content from the tool-calling context; remove or human-gate the outbound channel; require approval before exfil-capable tool calls), the severity mapping (unmitigated trifecta = High by default, Critical when a successful injection would expose sensitive/cross-tenant/production data), and the incident citation.
2. **Applicability templates** (`gate-applicability.template.yml` + `gate-applicability.output.template.yml` + both scaffold twins): add a `lethal_trifecta` block under the Gate 15 (`ai_rag_agent_security`) entry — `private_data_access`, `untrusted_content_exposure`, `outbound_channel` (each true/false/unknown), `legs_present` guidance, `mitigation`, and `human_confirmation_required: true` when >=2 legs. The output template carries always-on defaults consistent with its existing style.
3. **Standards** (`security-shipping-standards.md` + twin): one line in Gate Confirmation — an agent/tool-chain with all three trifecta legs is high-risk by default and needs a human-confirmed mitigation or a broken leg.
4. **Delta spec** `specs/launchguardian.md`: ADDED requirement "Gate 15 applies the lethal-trifecta test" with WHEN/THEN scenarios. Sync creates `sdd-plus/specs/capabilities/launchguardian.md` (Purpose = short pointer to the framework spec).
5. Verify: diff each edited pair for byte-identity; `check_sync.py`; `sdd.py verify`; verifier subagent (faithfulness + no gate drift); sync; archive; release 0.4.0 (Owner-gated).

## Files Expected To Change

- `sdd-plus/specs/launchguardian-framework.md` (+ `assets/project-scaffold/` twin)
- `sdd-plus/security/gate-applicability.template.yml` (+ twin)
- `sdd-plus/security/gate-applicability.output.template.yml` (+ twin)
- `sdd-plus/standards/security-shipping-standards.md` (+ twin)
- `sdd-plus/changes/gate15-lethal-trifecta/specs/launchguardian.md` (delta) -> `sdd-plus/specs/capabilities/launchguardian.md` (on sync)
- `CHANGELOG.md` (at release)

## Risks

- **Dual-copy drift**: editing the root copy but not the scaffold twin ships stale guidance to new installs (a known past bug class). Mitigation: every edit applied to both; a diff check per pair before verify.
- **Gate-name/number drift** across the three normative homes (framework spec, standards list, applicability templates). Mitigation: the verifier explicitly checks consistency; grep for "Gate 15" across the tree.
- **Overreach into other v0.4 gates**: the trifecta subsection could tempt supply-chain/RLS additions. Mitigation: stated stop condition; those are separate packets.
- **Faithfulness to evidence**: the rule must match what the sources actually established (structural; RLS/read-only don't fix it). Mitigation: cite the research note; verifier checks against it.

## Rollback

Every edit is additive prose/YAML. Reverting the six files restores the prior Gate 15 wording exactly; the new capability spec and delta are deletable. No code, no data, no migration. `git revert` of the release commit is clean.
