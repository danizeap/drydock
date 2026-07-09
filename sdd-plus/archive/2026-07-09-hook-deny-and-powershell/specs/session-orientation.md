# Spec Delta: session-orientation (hook-deny-and-powershell change)

Capability: session-orientation

## MODIFIED Requirements

### Requirement: Honest guardrail liveness probe
The hook SHALL report a guard as "live" only when running that guard under the current interpreter emits a JSON `permissionDecision: deny` on stdout whose reason contains the guard's expected block fragment on a destructive probe payload, AND the benign control payload produces no deny — both exiting 0 (the guards now deny via the JSON protocol, not exit 2). Any other outcome SHALL be reported as "degraded" (named) or "unverified". The verdict SHALL claim only what it verified and SHALL be freshly measured each session. The probe correctly reflects the wrapped `python3 X || python X` chain because the JSON-deny protocol exits 0, so the interpreter fallback never fires on a deny; the wrapped chain itself is separately regression-tested.

#### Scenario: Live only on a genuine JSON deny
- **WHEN** a guard emits a JSON deny with its expected reason on the destructive probe and no deny on the benign control
- **THEN** it is reported "live"

#### Scenario: A guard that fails open is not "live"
- **WHEN** a guard is replaced by one that allows the destructive probe (no deny emitted)
- **THEN** it is reported "degraded", never "live"
