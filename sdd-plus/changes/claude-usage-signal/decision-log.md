# Decision Log

## Change

claude-usage-signal

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-27 | Correct the old claim to: no documented structured Claude quota read has been established within Drydock's credential boundary. | The public widget proves a programmatic private OAuth path exists, while also proving that path needs credential-bearing code. | Retain the absolute "no programmatic way" claim; describe the private endpoint as an official API. |
| 2026-07-27 | Drydock consumes only a sanitized provider snapshot and never tokens or raw provider responses. | Capacity numbers are useful; credential custody and provider schema are unnecessary trust expansion. | Read `.credentials.json`; port Keychain access and token refresh. |
| 2026-07-27 | The MVP supports manual or external-broker snapshots and feature-detects any future official structured command. | This is useful on Windows today without violating the blueprint or betting on a private endpoint. | Block all usage work pending an official API; scrape the interactive `/usage` TUI. |
| 2026-07-27 | Usage is advisory and cannot authorize effects or prove convergence. | The snapshot is unsigned, user-writable, potentially stale, and account-wide. | Treat sufficient quota as permission to execute; use usage as enforcement evidence. |
| 2026-07-27 | Provider failures and stale data return `unavailable`; last-good data may be displayed only with explicit staleness. | Absence of evidence cannot become a positive routing signal. | Fail open using cached values; treat provider failure as zero capacity. |
| 2026-07-27 | A credential-owning helper requires a new Owner-approved boundary decision. | It would contradict the current normative no-credential statement and add token rotation, storage, and supply-chain risk. | Quietly embed the widget mechanism in Drydock. |
