# Evidence: Claude Usage Signal

## Public implementation reviewed

- Repository:
  `https://github.com/diegocp01/top_bar_claude_code_usage`
- Reviewed branch identity:
  `68dcf3666fb5253e28a79b43049bee86301338e3`
- The README and `Sources/ClaudeCodeUsageMenuBar/main.m` state and implement:
  macOS Keychain read of `Claude Code-credentials`; token refresh when needed;
  `GET https://api.anthropic.com/api/oauth/usage`; beta header
  `oauth-2025-04-20`; parsing of `five_hour`, `seven_day`, and optional weekly
  Opus usage; last-good caching and rate-limit backoff.

Inference: a machine-readable usage source existed for that observed
implementation. This suggests a possible path for a process willing and able
to read Claude credentials. It does not prove that the endpoint remains
available, public, documented, stable, permitted, or acceptable inside
Drydock.

## Current-machine read-only observation

- `C:\Users\Daniel Paez\.local\bin\claude.exe --version` reported Claude Code
  `2.1.173`.
- A read-only fixed-string scan of that binary observed
  `oauth-2025-04-20`, `five_hour`, `seven_day_opus`, and
  `seven_day_sonnet`.
- No Fable-specific window string was established.

Binary strings corroborate that the installed build knows related usage
schema terms. They do not prove response availability for this account,
endpoint stability, or semantic equivalence across releases.

## Current-machine Codex capacity observation

- The installed `codex.exe` app-server completed the documented initialize /
  initialized handshake and returned `account/rateLimits/read` without a model
  call.
- The response contained a main `codex` weekly bucket and a separately named
  model bucket. This proves the credential-free Codex collection mechanism on
  this installed build at that moment; the point-in-time percentages are not
  persisted as packet evidence.
- The official app-server schema exposes `usedPercent`,
  `windowDurationMins`, and `resetsAt`. It does not by itself establish whether
  every provider window should be modeled as fixed-reset.

## Credential container identification without content access

- A top-level directory listing identified
  `C:\Users\Daniel Paez\.claude\.credentials.json` as a regular named entry.
- The file contents were not opened, parsed, copied, hashed, or displayed.
- `claude auth status --json` confirmed authenticated first-party Claude Max
  status, but authentication does not prove usage endpoint operation.

## Architecture peer review

- A 26,649-byte self-contained packet was sent to `claude-opus-5` through
  Drydock's `StructuredOutput`-only adapter with no shell, file, web, browser,
  or MCP tools.
- The call cost reported by the Claude CLI was USD 0.4777815 and returned four
  blockers. The structured summary is preserved in
  `claude-architecture-review-round-1.json`.
- This is review evidence, not credential or endpoint evidence.
- A 38,728-byte round-two submission was refused before provider spawn because
  the durable `plan_peer` phase had exhausted its configured provider
  reservation and the cumulative input-byte reservation. This is envelope
  evidence, not a second review; no reset or alternate-model call was made.

## Existing normative boundary

`docs/CODEX_HOST_BUILD_BLUEPRINT.md` states that Claude authentication remains
owned by Claude Code and Drydock SHALL never read, copy, store, or log Claude
credentials.

## Actions deliberately not taken

- Did not open any Claude credential file or credential-store item.
- Did not call Anthropic's usage or token endpoints.
- Did not refresh, copy, display, or persist any token.
- Did not make a live Claude usage-endpoint or credential-refresh call.
- Did not claim current remaining capacity from source-code or binary evidence.
