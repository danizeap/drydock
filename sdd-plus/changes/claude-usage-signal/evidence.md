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

Inference: a machine-readable usage source exists for a process willing and
able to own Claude credentials. This does not prove that the endpoint is
public, documented, stable, or acceptable inside Drydock.

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

## Existing normative boundary

`docs/CODEX_HOST_BUILD_BLUEPRINT.md` states that Claude authentication remains
owned by Claude Code and Drydock SHALL never read, copy, store, or log Claude
credentials.

## Actions deliberately not taken

- Did not open any Claude credential file or credential-store item.
- Did not call Anthropic's usage or token endpoints.
- Did not refresh, copy, display, or persist any token.
- Did not make a live Claude model call.
- Did not claim current remaining capacity from source-code or binary evidence.
