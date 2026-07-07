# Spec Delta: owner-brief (owner-brief change)

Capability: owner-brief

## ADDED Requirements

### Requirement: Best-effort, category-only event ledger
The system SHALL provide `append_event()` in the shared hook module, writing one NDJSON line (date-only `ts`, `hook`, `action`, `category`) per event to a per-user, per-project ledger file (hashed project path, O_APPEND, one complete line per single write, size cap with opportunistic swallowed rotation, never fsync). The four guard/gate hooks (packet_guard deny/warn, protect_secrets deny, git_safety deny, completion_gate nudge) SHALL append only AFTER a non-silent verdict is decided — for the exit-2 guards after the verdict bytes are written and flushed; for the completion gate after the nudge is durably persisted (its persist-before-speak contract; the gate's fail direction is silence, so an append anomaly can at worst cost telemetry, never repeat a nudge). The silent/allow path performs no ledger I/O. Categories SHALL be validated at the sink against a frozen allowlist (unknown values coerce to a generic token, never written verbatim); no path, command, content, or message text is ever written. Every error SHALL be swallowed: a failed, slow, or impossible append MUST NOT change any hook's verdict, output, exit code, or delivery timing. When `DRYDOCK_PROBE=1` is present in the environment, append_event SHALL no-op (verdict logic never reads this variable). The reader SHALL reject symlinks and non-regular files, read only a bounded tail window with a per-line length cap, skip malformed lines, probe all candidate state-dir bases, and treat an unreadable ledger as "no history available", never as zero events.

#### Scenario: Append failure cannot change a verdict or its delivery
- **WHEN** the ledger location is unwritable or pathologically slow and git_safety evaluates a destructive command
- **THEN** the exit code, stdout, and stderr are byte-identical to a run with a healthy ledger

#### Scenario: Events carry categories, not content
- **WHEN** a caller passes a category containing a path or free text
- **THEN** the written line contains only an allowlisted or generic token, never the input text

#### Scenario: Liveness probes leave the ledger untouched
- **WHEN** session orientation probes the guards with DRYDOCK_PROBE=1 set
- **THEN** the guards still block as required and the ledger is byte-identical before and after

#### Scenario: Hostile ledger degrades to absence
- **WHEN** the ledger is a symlink, oversized, torn mid-line, or contains non-UTF8 or giant lines
- **THEN** the reader skips or rejects without crashing and reports what it could not read as unavailable

### Requirement: Deterministic FACTS engine with earned rungs
The system SHALL ship a plugin-only brief engine (`scripts/brief.py`, stdlib-only, no scaffold copy) that resolves its shared module strictly from its own plugin location (never cwd or project tree) and derives a structured FACTS block exclusively from repository and ledger state. Promise-ladder rungs SHALL be assigned by an ascent-requires-positive-evidence rule: a packet is an idea unless tasks.md exists with at least one checkbox; being-built requires checkboxes; built-not-yet-checked requires at least one checked and zero pending; the checked rung requires a `## Result` section affirmatively matching a closed PASS grammar — NOT VERIFIED, BLOCKED, FAIL, a missing heading, or unparseable text freeze the item at built-not-yet-checked with an explicit "record present but not a pass" marker. The engine SHALL NOT reuse the completion gate's claimed-done parsers. Archived items SHALL be demoted when their record shows waived gates (an `## Override` entry) or a non-PASS Result ("archived with recorded exceptions"), and artifact-incomplete archive directories SHALL render as "archive record incomplete" with no rung. The Owner-language line SHALL travel in a field named `goal`, truncated to one sentence. Ledger-derived counts SHALL carry machine-coverage bounds (sessions since ledger creation, on this computer) and a visibility marker when project history predates the ledger. A repository without Drydock SHALL yield a distinguished not-initialized FACTS block. Every unreadable source SHALL appear as an explicit `unavailable` marker — absence SHALL be distinguishable from zero. Rungs, counts, provenance classes, and availability SHALL be assigned only by deterministic code.

#### Scenario: A forged or negative verification result cannot mint the checked rung
- **WHEN** verification.md contains a bare "PASS." with no Result heading, or a Result of NOT VERIFIED
- **THEN** the item renders at built-not-yet-checked, never as checked

#### Scenario: A forced archive is distinguishable from a gated archive
- **WHEN** an archive's decision-log records an Override or its Result is not an affirmative pass
- **THEN** the item renders as archived-with-recorded-exceptions with a your-move line, not as done & documented

#### Scenario: Claimed-done work is distinguishable from verified work
- **WHEN** a packet's tasks are complete but verification.md is still Pending
- **THEN** the FACTS block places it on the built-not-yet-checked rung

#### Scenario: Quiet is never conflated with safe
- **WHEN** the ledger was created after the project's oldest archived work, or no ledger is readable
- **THEN** the FACTS block carries the not-visible-here marker or `unavailable`, never a bare zero

### Requirement: Verified provenance is earned by a recorded gate run
The system SHALL record a `verify-run` ledger event (packet name plus packet content-hash) only when `brief.py --record-verify <name>` itself re-runs the deterministic packet gate and that gate genuinely passes. The engine SHALL caption a checked item "confirmed on this computer" only when a verify-run event's hash matches the packet's current content-hash; a filled PASS Result with no matching event renders as "checked & recorded" (recorded-claim provenance), and any post-verification packet edit demotes the caption automatically. The word "independently" SHALL never be rendered from repository text alone.

#### Scenario: Typing a pass cannot fabricate confirmation
- **WHEN** an agent writes a PASS Result by hand and no matching verify-run event exists
- **THEN** the item renders as checked-and-recorded, not as confirmed on this computer

#### Scenario: Editing after verification demotes
- **WHEN** a packet changes after its recorded verify-run
- **THEN** the confirmation caption disappears until the gate is re-run

### Requirement: Owner-brief rendering and status-file contract
The `/drydock:brief` command SHALL render ONLY what the FACTS block contains, translated into plain language in the Owner's own language: no new facts, no states or counts the block does not assert, absence rendered as absence, framework vocabulary kept off the surface, goal fields presented as goals (never as achieved outcomes), each item ending in either "nothing needed from you" or "your move:" with exactly one decision, prevention phrased as recoverable governed pauses with the honest false-alarm cost stated, and the command never run unprompted. OWNER_STATUS.md SHALL be authored only by the engine's `--write-status` path from frozen per-language label sets (recorded as a lang code in the file's machine comment and reused on regeneration): a deterministic snapshot opening with a visible staleness warning ("generated <date> — anything after this date is not reflected"), carrying the git HEAD short-sha when readable (else "commit: unavailable"), the project fingerprint, and per-rung "as of <date>" captions. When current facts match the embedded fingerprint the file SHALL NOT be rewritten. The first write SHALL end with the Owner's explicit one-time choice: commit the file (visible on GitHub, lags by design) or gitignore it (private to this machine). On a not-initialized repository the command SHALL say so in one sentence and SHALL NOT write the file.

#### Scenario: The model cannot upgrade a claim
- **WHEN** the FACTS block reports an item at built-not-yet-checked with a goal line
- **THEN** the rendered brief presents the goal as a goal and the item as not yet checked, never as done or verified

#### Scenario: The status file is deterministic and self-dating
- **WHEN** --write-status runs twice on identical facts and language
- **THEN** the bytes are identical, the file leads with its generation date, and no second write occurs
