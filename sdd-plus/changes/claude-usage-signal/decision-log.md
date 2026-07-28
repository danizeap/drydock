# Decision Log

## Change

claude-usage-signal

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-27 | Correct the old claim to: no documented structured Claude quota read has been established within Drydock's credential boundary. | The public widget suggests a programmatic private OAuth path existed for one implementation, while also showing that path needs credential-bearing code; it does not prove current availability or permission. | Retain the absolute "no programmatic way" claim; describe the private endpoint as an official API. |
| 2026-07-27 | Owner correction: automatic dual-provider capacity awareness is mandatory; a manual snapshot is not an MVP. | Smart delegation must preserve both five-hour and weekly runway without asking the Owner to act as telemetry glue. | Manual values; usage dashboard only; route after a provider fails. |
| 2026-07-27 | Ship one installation with a dedicated credential-owning Claude broker process; keep tokens and raw responses outside the pilot and scheduler. | Full automation and the one-install product constraint require some trusted component to obtain Claude usage until an official command exists. | Separate product installation; put credential handling in the core pilot; abandon automatic Claude telemetry. |
| 2026-07-27 | Normalize Codex and Claude into overlapping provider windows and route on the lowest reserve-adjusted margin. | A provider can have ample weekly capacity and still exhaust its five-hour window; raw percentages are not comparable across different resets. | Compare one headline percentage; route round-robin; fixed provider preference. |
| 2026-07-27 | Preserve explicit flagship reserves for plan negotiation and cross-review before allocating execution work. | Pure throughput optimization could consume the capacity Drydock needs for epistemic checks. | Let the optimizer spend all available capacity; reserve a fixed number of calls without usage evidence. |
| 2026-07-27 | Learn burn and task costs from sanitized deltas and actual call metadata, with visible confidence and conservative cold-start defaults. | Smart allocation needs expected cost, but shared-account data and small samples do not justify false precision. | No cost model; exact token attribution claims; permanent hand-tuned ratios. |
| 2026-07-27 | Missing or stale telemetry yields degraded/unavailable routing, never positive headroom. | Absence of evidence cannot become a positive result. | Fail open using cached values; treat provider failure as zero capacity. |
| 2026-07-27 | Usage evidence is advisory scheduling input and cannot authorize effects or prove convergence. | The signal may be stale, account-wide, or broker-controlled; governance authority remains separate. | Treat sufficient quota as permission to execute; use usage as enforcement evidence. |
| 2026-07-28 | Treat the Windows broker as a same-user anti-accident boundary, not hostile credential isolation. | Claude credentials are user-scoped, so the pilot, workers, broker, debuggers, and malware under the same principal can reach the same store; process separation still reduces accidental token flow. | Claim a separate process is isolation; provision a separate principal that cannot read the existing user credential. |
| 2026-07-28 | Open Claude credential state read-only and never refresh, rotate, or write it. | Refresh-token rotation could invalidate concurrently running Claude Code clients, and Claude Code does not participate in a Drydock lock protocol. | Copy the widget's refresh flow; write refreshed credentials back to Claude state. |
| 2026-07-28 | Keep MVP routing ordinal and recommendation-only. | Task history is token-denominated while capacity is quota percentage; shared-account deltas cannot establish a Drydock-specific conversion. | Pretend tokens map to quota percent; block all automatic capacity recommendations until cardinal units exist. |
| 2026-07-28 | Make fixed-reset, sliding, and unknown window semantics first-class. | Reset-horizon arithmetic is invalid for sliding or unknown provider windows. | Treat every `resets_at` value as proof of a fixed reset. |
| 2026-07-28 | Require pilot review before dispatch and make reserve-consuming options structurally infeasible. | The scheduler is an orchestration advisor, not side-effect authority; showing reserve waivers as lower-ranked normalizes an invalid choice. | Enable automatic dispatch in the MVP; rank reserve-waiving alternatives. |
