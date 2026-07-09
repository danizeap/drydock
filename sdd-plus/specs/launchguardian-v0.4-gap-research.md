# LaunchGuardian v0.4 — Gap Research & Roadmap

**Status:** research input for a future change packet (not yet a packet). Durable so the work behind it is not lost.
**Provenance:** deep-research harness, 2026-07-08 — 5 search angles, 26 sources fetched, 128 claims extracted, 25 adversarially verified (3-vote). The synthesis agent was cut off by session limits; this note is the hand-synthesis from the captured claims. Confidence tiers below are exact — respect them.
**Companion:** this covers WHAT the gates should be (content). The process improvements (HOW gate verdicts are trusted) are in the second half.

---

## Verdict

The 22 gates are structurally sound but scoped for a 2023 web app, not a 2025 agent-wired, BaaS-backed, AI-generated vibe-coded app. Three real coverage gaps, one confirmed hard. No gate is *wrong*; several are scoped too narrowly to catch the dominant real-world failure inside them.

## Evidence — by confidence tier

### CONFIRMED (survived 3-vote adversarial verification)

- **The "lethal trifecta" is the signature threat for this exact audience, and Gate 15 as written misses it.** Documented incident (generalanalysis.com, Jul 2025; corroborated by Simon Willison and Supabase's own defense-in-depth-mcp post): a Supabase MCP server + an IDE agent that reads customer support tickets. Attacker hides instructions in a ticket; the agent, holding a `service_role` key, executes them as SQL and exfiltrates the database.
  - Root cause is **structural**: an LLM cannot separate instructions from data (confused-deputy). Not a patchable bug. [3-0]
  - **Succeeds with RLS correctly enabled**, because `service_role` bypasses RLS entirely. [2-0]
  - Implication: Gate 15's "tool permissions" point-check is insufficient. The risk is the *combination* — private data + untrusted content + outbound channel — which read-only mode and RLS do not neutralize.

### REFUTED (killed by verification — do NOT cite)

- ~~"1 in 9 vibe-coded apps leak DB keys (11.04%, 20,052 scanned)"~~ — **killed 0-2.** The *phenomenon* (BaaS credential / RLS-off leakage) is real and multiply-reported (Lovable CVE-2025-48757; the Tea app breach; MoltBook), but this specific statistic did not survive. Cite the phenomenon, never this number.

### STRONGLY SOURCED, verification cut off by session limit (primary sources; treat as high-confidence-unverified)

- **CI/CD pipeline compromise is a class Gate 10 does not own.** tj-actions/changed-files (CVE-2025-30066, Mar 2025, 23,000+ repos): attackers repointed mutable version tags at a malicious commit; payload dumped CI secrets into build logs (no outbound C2 needed). Chained from a prior reviewdog action compromise (CVE-2025-30154). Gate 10 covers *app dependencies*, not compromised GitHub Actions, workflow injection ("pwn requests"), mutable-tag references, self-hosted-runner persistence, or secrets-in-logs. Mitigation the sources stress: pin Actions to full commit SHAs. (CISA, Unit 42)
- **Install-script execution beats CVE scanning as the top supply-chain vector.** Shai-Hulud npm worm (CISA alert 2025-09-23, 500+ packages; "2.0" Nov 2025, ~700 packages + 25,000 exfil repos, 775 GitHub tokens + ~788 cloud creds harvested). Ran on `npm install` via pre/post-install scripts; self-propagating via stolen npm creds. A freshly-trojanized package has no CVE yet — so Gate 10's "SBOM + vuln thresholds" scope structurally misses it. (CISA, Unit 42, Wiz)
- **Slopsquatting** — attackers pre-register package names that AI models hallucinate. AI-specific; hits this audience directly (the AI writes their package.json). Named nowhere in the 22 gates. (Trend Micro AI Security)
- **OWASP Top 10 *2025* shifted under the framework**: two NEW categories — **A03 Software Supply Chain Failures** and **A10 Mishandling of Exceptional Conditions** (improper error handling / failing open) — plus Security Misconfiguration risen to #2. The framework predates these. (owasp.org)
- **Stripe webhook signature bypass** (CVE-2026-41432): empty signing secret → forged webhooks → quota/payment fraud. Gate 13 says "verify webhooks" generically; this is the concrete, named failure. (GitHub Advisory)
- **noAuth / OAuth-OIDC integration flaws** still affect a meaningful share of SaaS (thehackernews, 2025-06). Gate 8 covers first-party auth; third-party OAuth/OIDC integration is thinner.

## Recommended gate changes for v0.4 (evidence-backed; no more research needed)

1. **Re-scope Gate 15** from a permissions checklist to a **lethal-trifecta structural check**: does any agent/MCP simultaneously (a) touch private data, (b) ingest untrusted content, and (c) have an outbound channel? If all three, that is the finding — independent of RLS/read-only. *(CONFIRMED, audience-critical — highest priority.)*
2. **Split/expand Gate 10** to explicitly name **install-script execution, SHA-pinned Actions, lockfile integrity, and slopsquatting** — supply chain as OWASP 2025 now ranks it (A03).
3. **Add CI/CD pipeline integrity** as its own concern (or an explicit Gate 10 sub-scope): workflow injection, mutable action tags, self-hosted-runner persistence, secrets-in-build-logs.
4. **Sharpen Gate 6/16** to name the vibe-coding signature failure concretely: **RLS enabled on every table; the public anon key cannot read what it shouldn't** — the #1 real-world failure for the Supabase/Firebase stack.
5. **Consider a new gate or A10 mapping** for "fail-open / exceptional-condition handling" — OWASP made it top-10 for 2025.
6. **Gate 13**: name Stripe/webhook signature-secret verification concretely (empty-secret bypass).

Priority by incident evidence: **1 (confirmed) > 2 = 3 (mass-scale 2025 incidents) > 4 (dominant BaaS failure) > 5, 6.**

---

## Process improvements (the HOW — from the pre-research design discussion)

These are independent of the gate list and were the original v0.4 motivation. The self-certification hole we killed in verification (v0.2.1) still exists in LaunchGuardian one layer up.

- **Evidence-backed PASS.** A gate "passed" must be *derivable* from a machine-authored scan record (commit sha, tool versions, finding counts, timestamps), not declared by an agent typing "PASS". Same shape as `brief.py --record-verify`. The promise-ladder's top rung ("safe for customers") currently has no deterministic source — this is its source.
- **Provenance labels on every gate**: machine-scanned / AI-reviewed / human-confirmed. The Owner sees which kind of "passed" each gate is, never an undifferentiated green. Scanner-not-installed renders as "never scanned on this computer", not silence (today's non-strict mode silently skips missing scanners — a fail-toward-false-peace polarity bug by our own standards).
- **Applicability is proposed, challenged, and rendered with reasons** (Owner's insight): agent-written N/A stays — most gates legitimately don't apply to a given project. But the CLI's repo profiler should *contradict* wrong scoping: claims "no database" but a migrations/ dir exists → challenge; claims Gate 15 N/A but anthropic/openai in deps → challenge; claims "no auth" but a /login route exists → challenge. The verdict stays human/agent-owned; the machine only flags contradiction. And the Owner surface renders N/A gates *with their reasons* ("8 of 22 don't apply: no payments, no AI, single-user...") so lazy scoping can't hide from the one human who knows the product.
- **Fourth failure mode named:** honest-but-wrong N/A (agent scopes a gate away in good faith but mis-reads the app). The applicability challenge above is its answer.
- **Continuous, not ceremonial.** Vibe coders deploy continuously; they don't "launch". Attach security review to the lifecycle: a packet touching auth/data/deploy paths gets a deterministic archive gate requiring a fresh scan record; CI runs the scan on every push. "Launch review" becomes the deep pass, not the only pass.
- **Owner-language rendering.** Scan results flow through the brief pipeline: consequence language, "your move: one decision", skipped/forced gates surfaced like forced archives ("closed with recorded exceptions").
- **Step zero: audit the CLI itself.** `launchguardian-cli` sits at 0.1.1 — it predates everything the last seven releases taught us. It probably needs the same audit + red-team + test-harness treatment Drydock got pre-0.1.5, before we lean harder on it as the evidence source.

---

## Process lesson (meta)

This research cost three session limits because the deep-research harness fans out to 100+ agents (3 verify votes × 128 claims). See memory `deep-research-is-expensive`. For future gap analyses: direct WebSearch/WebFetch, or one tightly-scoped harness run, and salvage partial output from disk rather than resuming.

## Sources (primary, retained)

- generalanalysis.com/blog/supabase-mcp-blog · supabase.com/blog/defense-in-depth-mcp · simonwillison.net/2025/Jul/6/supabase-mcp-lethal-trifecta
- cisa.gov npm alert 2025-09-23 · unit42.paloaltonetworks.com/npm-supply-chain-attack · wiz.io/blog/shai-hulud-2-0-ongoing-supply-chain-attack
- cisa.gov tj-actions alert 2025-03-18 · unit42.paloaltonetworks.com/github-actions-supply-chain-attack
- trendaisecurity.com slopsquatting · owasp.org/Top10/2025 · genai.owasp.org/llm-top-10 · cwe.mitre.org/top25/archive/2025
- github.com/advisories Stripe webhook CVE-2026-41432 · thehackernews.com 2025-06 noAuth
- Lovable CVE-2025-48757 (thenextweb, theregister) · Tea app breach (barracuda) · MoltBook (ogwilliam.com)
