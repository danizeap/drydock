# Spec Delta: launchguardian (gate-rescopes-2025 change)

Capability: launchguardian

## ADDED Requirements

### Requirement: Gate 10 covers supply-chain execution and CI/CD integrity
Gate 10 (Dependency, SBOM & Supply Chain) SHALL cover more than known-CVE scanning. It SHALL assess: dependency install-script execution (pre/post-install lifecycle scripts, the dominant documented 2025 compromise vector, which known-CVE scanning does not catch on a freshly trojanized package); lockfile integrity and version pinning; third-party CI/CD workflow components pinned to immutable commit SHAs rather than mutable tags; workflow-injection, self-hosted-runner persistence, and secrets exposed in build logs; and slopsquatting (packages published under names AI coding tools hallucinate). These SHALL be framed to their primary-source evidence (e.g. the Shai-Hulud npm worm, CISA alert September 2025; the tj-actions/changed-files compromise, CVE-2025-30066, March 2025; OWASP Top 10 2025 A03 Software Supply Chain Failures), without asserting more certainty than the sources support.

#### Scenario: A freshly trojanized dependency with an install script is in scope
- **WHEN** a project adds or updates an npm/pip dependency that runs a pre/post-install script
- **THEN** Gate 10 treats install-script execution as a supply-chain risk even when no CVE is yet published for that version

#### Scenario: Mutable CI action references are flagged
- **WHEN** a CI workflow references a third-party Action by a mutable tag rather than a pinned commit SHA
- **THEN** Gate 10 flags it as a CI/CD supply-chain integrity risk

### Requirement: Gates 6 and 16 name the BaaS row-level-authorization failure
Gate 6 (API Auth & Object Authorization) and Gate 16 (Multi-Tenant & Internal Permission Isolation) SHALL name the concrete Backend-as-a-Service failure that dominates this audience: Row-Level Security (or equivalent row-level authorization) enabled on every table that holds private or tenant data; the public/anon client key unable to read or write beyond its intended policy; and a privileged service/admin key never shipped in client-side code. The requirement SHALL cite the RLS-off breach class as a phenomenon (e.g. Lovable CVE-2025-48757, the Tea app breach) and SHALL NOT cite the specific "1 in 9 / 11%" scan statistic (refuted in verification).

#### Scenario: A table without row-level authorization is a finding
- **WHEN** a BaaS-backed project exposes a table of private or tenant data with RLS disabled or no row-level policy
- **THEN** Gate 6/16 records it as a high-risk object-authorization failure

#### Scenario: A service key in client code is a finding
- **WHEN** a privileged service/admin key that bypasses row-level authorization is present in client-delivered code
- **THEN** Gate 6/16 (with Gate 4/5) records it as a critical exposure
