"""Drydock conductor — read-only multi-agent delegation to Codex.

Discovers the current Codex core, reads Codex's remaining quota, and delegates
bounded analysis/review tasks with schema-locked output. Read-only by
construction: no code path here can mutate the repository. Mutating delegation
is the separate `codex-enforcement-bridge` concern.
"""
from .codex_bridge import (  # noqa: F401
    discover_core,
    read_rate_limits,
    summarize_gauge,
    route,
    guard_outbound,
    delegate,
    delegate_file,
    build_exec_argv,
)
