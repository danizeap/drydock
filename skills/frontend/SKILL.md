---
name: frontend
description: Implement approved designs and client-side behavior without unauthorized redesign. Use for components, routes, client API integration, UI states, responsive behavior, accessibility basics, browser-side security, and design fidelity. Not for backend logic or design invention.
---

# Frontend Skill

Answers: can this approved design be implemented and connected to the real product without visual drift, fragile code, accessibility failures, browser-side security mistakes, or broken behavior? The agent implements approved designs; it does not invent or silently change them.

## Preflight

State: approved design source (mockup, design file, existing pattern, or explicit Owner approval to improvise); implementation mode (pixel-faithful / pattern-faithful / functional-first); design source of truth vs functional source of truth; required UI states; existing frontend patterns to follow; intended files; stop conditions.

## Core rules

- **Design fidelity**: follow the approved source. Deviations are listed explicitly, never silent. No approved source and non-trivial UI → ask, don't improvise.
- **Every meaningful view covers its states**: loading, empty, error, partial/degraded, success, and permission-denied where relevant. A view that only handles success is incomplete.
- **Follow existing patterns**: component conventions, styling system, state management, API client patterns. No new UI library, styling approach, or state framework without justification and approval.
- **Browser-side security**: no secrets or server config in client code or public env vars; no sensitive tokens in localStorage/sessionStorage when the project's auth pattern avoids it; user-controlled content is rendered safely (no unsanitized HTML injection); client-side checks are UX, never the security boundary — the backend enforces.
- **Accessibility basics**: semantic elements, labeled inputs, keyboard reachability, focus management on dialogs/navigation, sufficient contrast per design tokens.
- **Forms**: validation messages, disabled/double-submit protection, and failure behavior are defined.
- **Performance sanity**: no unbounded client-side loops over large datasets, no accidental waterfall fetching where the project has a batching pattern.

## Blocking rules

BLOCK if: non-trivial UI is built with no approved design source and no explicit approval to improvise; required UI states are missing; secrets/server config reach client code; user content is rendered unsafely; client-side checks are the only enforcement for a permission; a new UI/styling/state dependency appears without approval; or the change silently redesigns existing approved UI.

## Evidence

STANDARD: compact format plus approved design source, implementation mode, UI state coverage, and design deviations. FULL adds: component/route inventory, responsive behavior, accessibility review, browser security review, form behavior, performance sanity, Owner Summary.
