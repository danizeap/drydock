# Drydock as a Multi-Agent Orchestration Layer — Vision & Architecture Notes

**Status:** vision capture + architecture read. NOT a packet, NOT committed design. Preserves the Owner's idea dump (2026-07) so it survives, plus an honest analysis of what Drydock already provides, what is genuinely new, the hard parts, and the facts we must verify before building.

**One-line reframe:** Drydock stops being a governance framework that a single coding agent *follows*, and becomes the **coordination + governance layer above multiple frontier coding systems** (Claude Code / Fable 5 and Codex) and their model-specific sub-agents. Drydock is the conductor, not an instrument.

---

## 1. The Vision (Owner)

Run Claude Code (Max) and Codex (equivalent license) as **one coordinated development organization**, not two separate tools, with Drydock as the coordination layer.

- **Divide-and-conquer.** Every new task: both systems analyze it together, divide it by their actual strengths ("you take this, I'll take that, because you're better at X"), each does its part, they audit each other, combine results.
- **Usage-aware resource management.** Each system is self-aware of remaining usage + reset time + available models + per-model cost. Allocate work to burn the right usage on the right platform (e.g. the low-usage system does the "dumber-model" work; the high-usage system takes the heavy work). Avoid running out; avoid wasting unused quota.
- **Collaborative, documented strategy.** They build the project strategy together AND document it *as the task executes*: how it was analyzed, how divided, why each got its work, which models chosen and why, what each produced, how audited, problems found, corrections, decisions.
- **Mutual code auditing.** Not trust — one implements, the other reviews (errors, architecture, security, missing tests, bad assumptions), the first fixes; and vice versa. Two systems making each other's work *better*, not just producing more code.
- **Adversarial security.** For security, go adversarial: one builds/secures, the other tries to hack/exploit/bypass it, findings feed hardening; then reverse the roles. Active attack, not passive review.
- **Two PMs with an army of coders.** The felt experience: talk to top-level frontier models in Chat/Codex/Claude Code that understand intent, discuss with each other, build strategy, divide, delegate to sub-agents, choose models, review + test each other, correct, document, deliver.
- **Discovery — model-specific sub-agents.** Claude Code (Fable) can spawn a sub-agent and assign it a *specific* (cheaper) model. The Owner confirmed this exists and asked Codex whether it can too. This is the linchpin: frontier models orchestrate; sub-agents with chosen models execute.
- **Frontier-as-orchestrator.** Top models stay at the top level for thinking, conversation, planning, architecture, decomposition, risk, model selection, delegation, oversight, final review — and delegate implementation to sub-agents with the right model per subtask.
- **Deep, DYNAMIC model knowledge.** Drydock needs a deep understanding of each model's strengths (planning / coding / reading large code / debugging / review / security / adversarial / docs / repetitive-low-risk / complex-high-risk / cost). But NOT a rigid static table ("always this model for this category"). It must re-evaluate every situation: the exact task, context, complexity, risk, codebase state, available models, remaining usage, time to reset, each system's strengths, need for independent audit, parallelism, delegability. Explicit anti-goal: **lazy orchestration** ("give Sonnet all the reading, do the rest myself").
- **Maximize both ecosystems.** Reserve frontier reasoning for where it matters; direct leftover usage to appropriate work; when one runs out, the other continues; independent oversight from the *second* system; continuously balance quality / capability / usage / cost / speed / risk / context / verification.

The goal: extract the best of each system and make them operate as one team — divide intelligently, best model per moment, manage usage strategically, self-audit through an independent system, attack its own security assumptions, document decisions.

---

## 2. What Drydock already provides (the substrate — ~half of this is near-free)

The core Drydock thesis — *"durable facts live in git, never in chat memory"* — is exactly the substrate a multi-agent relay needs. Map the vision onto what exists:

| Vision element | Existing Drydock piece |
|---|---|
| Shared handoff / "know where the other was" | git log/diff + change packets + `sdd.py status` + the Resume playbook (`framework-usage.md` §6) — reconstruct state from reality, "never assume an old plan was implemented" |
| Documented strategy as execution happens | The **decision-log** + brief/plan/tasks/verification — Drydock already documents *why* as it goes. "Why each system got its work / which models / why" is a decision-log table. |
| Mutual auditing | The **verifier** concept — "review work you didn't do, in a fresh context, adversarially." Two *different* frontier models as reviewers = diverse review, stronger than one model self-checking. |
| Adversarial security | The pre-implementation **red-team workflow** pattern used throughout Drydock's own build — now with a real adversary from the *other* ecosystem. |
| Scale ceremony to the task | **LITE / STANDARD / FULL** modes + the framework-theater rule — already the "don't over-orchestrate a typo" principle. |
| Agent-agnostic rules | `AGENTS.md` is already the canonical cross-agent source of truth; `sdd.py` is the agent-agnostic lifecycle engine both can run. |
| Shared enforcement floor | (Planned) git pre-commit hook bridge — the deny-guards as a git hook fire for Claude Code, Codex, and a human alike; nobody can route around them. |

So "surprise → audit → propose → correct → document" is *nearly native*. The active packet is the handoff document; the owner-brief is the "where are we" dashboard; the archive is the "what shipped."

---

## 3. Genuinely new work

1. **The coordination mechanism** — how the two systems actually divide + hand off work (see hard parts).
2. **Model-selection intelligence** — a *living, updatable* capability prior + situational judgment (not a static table, not pure vibes; must survive monthly model churn).
3. **Usage-awareness** — reading remaining quota/reset/costs per platform (feasibility unknown — verify).
4. **The orchestration packet** — a documented division-of-work artifact: assignment, model choices, rationale, cross-audit results (mostly an extension of the existing decision-log).
5. **Cross-agent, cross-tool review + adversarial security as first-class rituals** (the pattern exists; wiring it between two tools is new).
6. **Attribution** — the event ledger / commits stamping which system did what, so audits read "Codex did this migration — check it."

---

## 4. The hard parts / honest risks (a partner names these)

- **Native real-time comms between the two tools DO NOT exist.** Claude Code and Codex are separate processes with no socket to each other. Coordination is necessarily via **shared artifacts (git/files)** + **the human (you) as the transport**, OR a single orchestrator process that can invoke both. A realistic v1 embraces "the human is the message bus; Drydock makes that structured, cheap, and stateful."
- **Who is the orchestrator?** Two shapes to choose between:
  - *Peer model*: Codex and Claude Code are equals coordinating through shared git state; you relay. Simple, but division is negotiated asynchronously through artifacts (clunky).
  - *Conductor model*: one layer (a Drydock orchestrator, or the chat model you talk to) decides the division and dispatches. Cleaner, but needs a driver that can actually invoke both tools.
- **Coordination overhead can exceed the benefit.** Two agents negotiating + auditing + documenting per task = heavy. Orchestration MUST scale with task size (inherit LITE/STANDARD/FULL). Do not two-PM a typo.
- **True parallelism on one repo = collisions.** Two agents writing the same tree stomp each other. "One sleeps while the other works" (serial relay) is actually *safer* — no concurrent writes. Real parallelism needs per-agent git worktrees/branches and a merge step.
- **Lazy orchestration is a real, hard-to-detect failure.** Mitigation is very Drydock: make the *division decision itself* documented and auditable — the other agent reviews the SPLIT and the model choices, not just the code ("was this a sensible division, or did one system hog the frontier model?").
- **The capability knowledge going stale** is the exact thing the Owner fears. It must be a revisable prior with a "last-updated / revisit-when-models-change" discipline, not a frozen mapping.

---

## 5. Open questions to VERIFY before designing around them (do not assume)

1. **Can each tool read its OWN remaining usage + reset time programmatically?** Claude Code shows usage in the UI; whether the *agent* can query its remaining quota is unconfirmed. If NOT: usage-awareness v1 falls back to the Owner telling it ("we're low on Codex") — which is exactly how the sub-agent-model trick was discovered. **This is the #1 feasibility gate for the usage-aware delegation.**
2. **Does Codex support sub-agent model assignment** like Claude Code's Agent/Task tool (`model` param)? Confirmed for Claude Code (in-use). Owner already asked Codex — **need Codex's actual answer.** This is the linchpin of frontier-orchestrator + cheap-workers.
3. **Is there ANY real-time channel, or is it strictly human/git-relayed?** Determines peer-vs-conductor and whether "divide together in real time" is possible or is really "divide via a shared plan file."

---

## 6. Proposed first bricks (small, proves the loop, everything layers on top)

1. **Git-hook enforcement bridge** — port the deny-guards to an agent-agnostic git pre-commit hook so the shared repo is safe for BOTH agents (and the human). Foundational; also the Codex tier-4 answer. Highest leverage.
2. **Orchestration packet section** — extend the change packet with a documented "division of work": who/what/which-model/why + cross-audit outcomes. ~90% is already the decision-log.
3. **Structured relay/handoff ritual** — the incoming tool reconstructs state (git + packets + Resume playbook) and audits the outgoing tool's work before continuing. Serial relay first (safer than parallel).
4. **Living model-capability note** — a revisable prior on model strengths + a situational-judgment checklist, with an explicit staleness/revisit discipline.
5. (Later, gated on Q1/Q2) usage-aware delegation + model-specific sub-agent dispatch + true-parallel worktrees.

**Sequencing principle:** make the repo safe for two agents (1) → make the division documented + auditable (2, 3) → add intelligence (4) → add autonomy/parallelism/usage-optimization (5) only after the feasibility gates are answered.

---

## 7. Codex capability audit — findings (2026-07-23)

Source: Owner ran the question list against Codex. The three feasibility gates are now RESOLVED, and several answers map onto Drydock almost verbatim.

### Gates resolved
- **Q1 usage self-awareness — YES, but only to an EXTERNAL controller.** The in-session interactive Codex agent cannot read its own quota. But `codex app-server` exposes a programmatic RPC `account/rateLimits/read` returning `usedPercent`, `windowDurationMins`, `resetsAt` (Unix secs) for a primary + secondary window. **Architectural consequence: the usage-aware orchestrator is a separate controller process, not the agent you chat with.** Cost awareness is qualitative only (terra < sol; Fast mode = 2.5× Standard) — routing uses coarse cost tiers, not exact multipliers.
- **Q2 model-specific sub-agents — YES on BOTH sides.** Codex: `spawn_agent({model, reasoning_effort, fork_turns})` in-session, or config `[agents] default_subagent_model`, or per-agent `.codex/agents/*.toml`; parallel up to 3 concurrent (config `max_concurrent_threads_per_session=8`); sub-agents share the working dir, return status+text (no schema guarantee in-session). Claude Code: confirmed firsthand — the Agent/Task tool takes a `model` param and workflows set model/effort per agent. **Frontier-orchestrator + cheap-workers is real in both ecosystems.**
- **Q3 coordination — YES, no human relay required.** Codex runs headless (`codex exec --json`), with **schema-constrained output** (`--output-schema` + `--output-last-message` → structured JSON back to a caller). And `codex mcp-server` exposes `codex(prompt, cwd?, model?, ...)` + `codex-reply(prompt, threadId)` as MCP tools — **Claude Code, being an MCP client, can call Codex directly.** Plus an experimental `app-server --listen ws://` socket. **The conductor model is buildable: one side dispatches to the other; git/files carry artifacts; the human is no longer the mandatory bus.**

### Bonus findings that de-risk the build
- **Codex hooks are nearly byte-compatible with Drydock's.** `.codex/hooks.json` has `PreToolUse` with `matcher` + `command` (+ a `commandWindows` variant), the script gets tool JSON on stdin, and it denies with the **exact same `permissionDecision: deny` protocol (exit 0)** Drydock uses — or exit 2 + stderr. **Drydock's `protect_secrets.py`/`git_safety.py`/`packet_guard.py` port to Codex almost verbatim** (matcher `^(Bash|apply_patch|Edit|Write)$`). The v0.5.0 JSON-deny migration is exactly what makes them cross-tool portable — unplanned but perfectly timed. (Codex's separate `commandWindows` field is also a cleaner cross-platform interpreter answer than Drydock's `python3 X || python X`.) Caveats: project hooks run only in trusted projects, can be disabled unless admin-pinned via `requirements.toml`, hosted tools may bypass, malformed/timeout responses fail open — a guardrail, not a hard boundary (same honesty as Drydock; pair with an OS sandbox for containment).
- **Git pre-commit hooks fire on Codex's `git commit`** (except `--no-verify`, remote-API commits, or a redirected `core.hooksPath`). The agent-agnostic git-hook bridge works for Codex.
- **AGENTS.md is read automatically by Codex** (documented discovery order + precedence); `CLAUDE.md` via `project_doc_fallback_filenames`. Drydock's existing "AGENTS.md canonical, CLAUDE.md is a Claude delta" design is exactly right.
- **Worktrees:** manual isolation works (`git worktree add` + `codex exec -C`); Codex desktop has managed worktrees under `$CODEX_HOME/worktrees`.
- **Handoff:** `codex exec - < HANDOFF.md` (stdin = full prompt), or `codex exec -C <worktree> "Read HANDOFF.md and continue"`. The wake-up ritual is concrete.

### Codex's own recommended integration pattern
1. Separate git worktrees for Claude Code and Codex. 2. Exchange tasks via `codex mcp-server` or `codex exec --json`. 3. `account/rateLimits/read` for quota-aware routing. 4. Share rules via AGENTS.md. 5. Hooks + external sandbox for enforcement.

### Reshaped architecture (post-audit)
- **The conductor is an external controller process** (reads both tools' rate limits, decides the division, dispatches, collects structured results, triggers cross-audit) — because quota-reading and dual-dispatch live outside any single interactive session. A lighter variant: Claude-Code-as-conductor calling Codex via `codex mcp-server`, with a thin helper for the rate-limit reads.
- **Enforcement bridge = mostly done work:** the existing Drydock hooks drop into `.codex/hooks.json` (protocol-compatible) + a git pre-commit hook → both agents governed by the identical deny-guards.
- **Isolation:** a git worktree/branch per agent + a merge step for parallel; shared worktree for serial relay.

### Claude Code side — audit findings (2026-07-23, claude-code-guide)
The symmetric picture is now complete. Combining both audits resolves the architecture.
- **Usage self-read — NO (the definitive answer to the last gate).** Claude Code has NO programmatic way to read its own remaining quota/reset. `/usage` is interactive UI only; `claude -p --output-format json` reports `total_cost_usd` for that one invocation (spend, not remaining); the Agent SDK has `max_budget_usd` (a cap you set to STOP at, not a value you can READ). **So quota-awareness is ASYMMETRIC: precise on Codex (app-server `account/rateLimits/read`), opaque on Claude.** Routing on the Claude side must be external cost-accumulation, a budget cap, or human-informed ("we're low"). Not a blocker — just means the conductor tracks Claude spend itself rather than querying it.
- **Headless + structured output — YES.** `claude -p --output-format json`, `--json-schema` for schema-validated output, stdin/file input, and the Agent SDK (Python/TS). Claude Code can be driven headless by a controller with structured results — the mirror of `codex exec --json --output-schema`.
- **Sub-agent model assignment — YES (confirmed both ways).** Frontmatter `model:`, `--agents` CLI, `CLAUDE_CODE_SUBAGENT_MODEL` env (precedence: env > per-call param > frontmatter > parent).
- **MCP bridge — CONFIRMED by combining the two audits.** Claude Code is an MCP *client*: it registers external stdio MCP servers via `.mcp.json` / `claude mcp add --transport stdio` and calls their tools as `mcp__<name>__*`. The Codex audit confirmed `codex mcp-server` publishes `codex(prompt, cwd?, model?)` + `codex-reply(prompt, threadId)`. **Therefore Claude Code can register Codex and call it directly as `mcp__codex__codex`** — each audit confirmed the half the other couldn't. This makes **Claude-Code-as-conductor** the natural shape: it can dispatch subtasks to Codex over MCP, run headless, and assign sub-agent models — with a thin external helper (or human) for the Claude-side quota it can't self-read.

### Resolved conductor architecture
- **Claude Code is the conductor** (MCP client → calls Codex as `mcp__codex__codex`; headless-capable; assigns sub-agent models). Codex is a first-class executor reachable over MCP.
- **Quota is asymmetric:** the conductor reads Codex's real remaining % via app-server, and *tracks* Claude spend by accumulation (or is told "we're low"). Route the low side to cheaper models / fewer sub-agents.
- **Both dispatch to model-specific sub-agents**, so the frontier-orchestrator + cheap-workers pattern runs inside each ecosystem AND across them.

### Revised first bricks (grounded)
1. **Enforcement bridge** — wire the existing hooks into `.codex/hooks.json` + a git pre-commit hook; verify a deny fires under Codex. Highest leverage, smallest new code (protocol already matches).
2. **Shared-law packaging** — AGENTS.md as the common rules (done) + a `.codex/config.toml` starter (hooks wiring, CLAUDE.md fallback, subagent defaults).
3. **HANDOFF.md relay ritual** — reconstruct → audit-the-other → continue; serial first.
4. **Conductor MVP** — a controller that reads Codex rate limits, dispatches one subtask via `codex exec --json --output-schema`, and hands the result to the other agent for audit. The genuinely-new piece.
5. (Layered) living model-capability note + usage-aware routing + parallel worktrees.

---

## 8. Empirical validation — live-fire on the Owner's machine (2026-07-23)

Before building the conductor, the two load-bearing assumptions were tested against the Owner's actual Windows install. **Both pillars are PROVEN with current tooling.** This section is ground truth, not docs.

### Both pillars green
| Pillar | Result | Evidence |
|---|---|---|
| Governor can **drive** Codex headlessly | ✅ flagship | `gpt-5.6-sol` → `BRIDGE_OK`, exit 0, ~7s, clean `turn.completed` |
| Governor can **read Codex's fuel** | ✅ | live `account/rateLimits/read`: Plus plan, weekly window, 5% used, ~free (no model turn) |

### Environment facts (Windows)
- Codex is the **MSIX desktop app** `OpenAI.Codex_26.715.10079.0` (process `ChatGPT.exe`). Its headless core is **NOT on PATH**.
- **Current core:** `%LOCALAPPDATA%\OpenAI\Codex\bin\<hash>\codex.exe` — `codex-cli 0.145.0-alpha.30` (~350 MB). The `<hash>` dir **changes on every update** → the conductor MUST **discover** it (glob newest `%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`), never hardcode.
- **Do NOT use** the stale sandbox copy `~/.codex/.sandbox-bin/codex.exe` (`0.119.0-alpha.28`): too old to run flagship (`gpt-5.6-*` → server 400 "requires a newer version of Codex"), and can't parse the app-written config (`service_tier=default`, reasoning-effort `max`). It only worked with `-c service_tier=fast` + an old model (`gpt-5.4-mini`). Version skew between the app's core and the sandbox copy is the trap.

### Drive invocation (proven)
```
<core>\codex.exe exec --json --ephemeral --skip-git-repo-check -s read-only \
  -m gpt-5.6-sol -C <working-dir> "<prompt>"
```
JSONL out: `thread.started` → `turn.started` → `item.completed`(`agent_message`) → `turn.completed`(`usage`). The current core runs flagship natively — **no `service_tier` override needed**.

### Fuel gauge (proven) — `codex app-server` over stdio JSON-RPC
Handshake: `initialize {clientInfo:{name,version}}` → (`initialized`) → `account/rateLimits/read` (params `null`). Response: `rateLimits.primary{usedPercent,resetsAt(unix s),windowDurationMins}`, `.secondary`, `.credits{balance,hasCredits,unlimited}`, `.planType`, plus `rateLimitsByLimitId` (keyed `codex`). Protocol confirmed offline via `codex app-server generate-json-schema --out <dir>`. Reader lives in scratch (`codex_fuel_gauge.py`) — becomes a conductor component. **This account:** Plus, primary = weekly (10080 min), `secondary: null`, credits `balance "0"`/`hasCredits false` → **hard weekly ceiling, no overflow cushion.**

### The context-tax lever (measured)
Codex auto-ingests the working root's context (`AGENTS.md`, repo docs). A trivial task cost **172,931 input tokens** with cwd = the drydock repo, but **16,156** with cwd = an empty scratch dir — a **~91% cut**. Delegation cost is a **dial**: run followers against a lean working root, and never delegate tasks too small to beat the baseline. Verified on the same 5-word prompt.

### Design implications for the conductor
1. **Discover** the current core under `%LOCALAPPDATA%\OpenAI\Codex\bin\*\` (newest); use it for BOTH `exec` and `app-server`.
2. Route flagship (`gpt-5.6-sol`) for lead-quality/high-stakes work; cheaper models for volume — the endurance play.
3. Read the gauge before routing; treat Codex (this plan) as a hard weekly bucket.
4. Control the per-delegation context tax via `-C` (lean working root).
5. **Verdict: feasibility proven end-to-end with current tooling. The reality-check phase is complete.**
