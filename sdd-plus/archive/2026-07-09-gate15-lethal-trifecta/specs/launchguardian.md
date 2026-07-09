# Spec Delta: launchguardian (gate15-lethal-trifecta change)

Capability: launchguardian

## ADDED Requirements

### Requirement: Gate 15 applies the lethal-trifecta test
Gate 15 (AI/RAG/Agent Security) SHALL be assessed as a structural combination check, not only a list of independent items. The framework SHALL define the "lethal trifecta" as the co-occurrence, in a single AI agent, MCP server, or LLM tool-chain, of all three of: (1) access to private or sensitive data, (2) exposure to attacker-influenced / untrusted content, and (3) an outbound channel able to send data or effects outside the trust boundary. WHEN all three legs are present, the configuration SHALL be treated as high-risk regardless of Row-Level Security or read-only settings, because a privileged service credential bypasses RLS and read-only access still permits reading private data, being injected, and exfiltrating through the outbound channel. The framework SHALL prescribe "break a leg" (removing or human-gating any one of the three) as the primary control, and SHALL map an unmitigated trifecta to High severity by default, escalating to Critical when a successful injection would expose sensitive, cross-tenant, or production data. The project applicability record SHALL be able to capture the three legs as recordable fields so the combination is durable evidence, not only prose.

#### Scenario: All three legs present is high-risk despite RLS
- **WHEN** an agent can read private data, ingests untrusted user content, and has an outbound channel, with Row-Level Security enabled
- **THEN** Gate 15 flags the trifecta as high-risk and RLS is not accepted as the mitigation

#### Scenario: Breaking a leg clears the trifecta finding
- **WHEN** one leg is removed or human-gated (e.g. the outbound channel requires per-action human approval, or untrusted content is isolated from the tool-calling context)
- **THEN** the trifecta finding is mitigated and the residual risk is recorded

#### Scenario: The trifecta legs are recorded as durable evidence
- **WHEN** a project completes its Gate 15 applicability record for an AI/agent feature
- **THEN** the three legs are captured as fields (present / absent / unknown) with the mitigation, not asserted only in prose
