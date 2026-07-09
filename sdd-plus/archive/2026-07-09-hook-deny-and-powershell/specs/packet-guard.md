# Spec Delta: packet-guard (hook-deny-and-powershell change)

Capability: packet-guard

## MODIFIED Requirements

### Requirement: Deny narrow high-risk work without a packet
The guard's Bash coverage SHALL extend to the `PowerShell` shell tool: high-risk write targets (schema migrations, new CI configs, container/deploy configs, the generated `OWNER_STATUS.md`) SHALL be denied whether the command runs through Bash or PowerShell. Write-target extraction for a PowerShell command SHALL use the shared PowerShell-aware extractor (native write cmdlets plus the POSIX forms PowerShell shares), so the deny tier cannot be escaped by switching shells. All existing suppression (test/fixture/docs segments) and the silent-allow-on-error contract SHALL be unchanged, and the guard SHALL continue to deny via the JSON protocol with exit 0.

#### Scenario: A PowerShell write into a high-risk path is denied
- **WHEN** `Set-Content migrations/0003.sql "..."` runs through PowerShell with no active packet
- **THEN** the guard denies it, as it would for the equivalent Bash redirection

#### Scenario: PowerShell writes under a test segment are still suppressed
- **WHEN** a PowerShell write targets `tests/fixtures/...`
- **THEN** the guard does not deny
