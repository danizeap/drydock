#!/usr/bin/env python3
"""Executor fleet — a pluggable interface over the coding executors the conductor
can drive. The conductor stops being "Claude + Codex" and becomes a FLEET manager:
given the stack the Owner has installed (Claude alone / +Codex / +Kimi / all three),
it knows which frontier tanks are available and how much fuel each has left.

Codex is the PROVEN adapter (live-fire verified). Kimi is STAGED: documented from
Moonshot's Kimi CLI / coding plan but NOT yet reality-checked on a machine where
it's installed — it reports as present-but-unverified and refuses to run until the
same Codex-style live-fire proof is done. Nothing claims to work until proven.
"""
import json
import os
import sys
from shutil import which

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # scripts/ -> `conductor` importable
from conductor import codex_bridge as cb  # noqa: E402


class ExecutorUnverified(RuntimeError):
    """An adapter that is documented but not yet reality-checked on this machine."""


class Executor:
    name = "base"
    verified = False            # has this adapter been live-fire proven here?
    subscription_window = True  # refilling quota window (vs pay-per-token balance)

    def available(self):
        """True if installed + usable on this machine. Presence != verified."""
        raise NotImplementedError

    def read_remaining(self):
        """{ok, remaining_percent, resets_in_hours, plan, ...} or {ok: false, ...}."""
        raise NotImplementedError

    def status(self):
        try:
            avail = bool(self.available())
        except Exception:
            avail = False
        out = {"name": self.name, "verified": self.verified, "available": avail,
               "subscription_window": self.subscription_window}
        if avail and self.verified:
            try:
                out["fuel"] = self.read_remaining()
            except Exception as e:  # noqa: BLE001
                out["fuel"] = {"ok": False, "error": str(e)}
        elif avail and not self.verified:
            out["fuel"] = {"ok": False, "staged": True,
                           "error": "installed but not yet reality-checked"}
        return out


class CodexExecutor(Executor):
    name = "codex"
    verified = True

    def available(self):
        return cb.discover_core() is not None

    def read_remaining(self):
        core = cb.discover_core()
        if not core:
            return {"ok": False, "error": "codex core not found"}
        gauge = cb.summarize_gauge(cb.read_rate_limits(core))
        if not gauge:
            return {"ok": False, "error": "could not read Codex rate limits"}
        return {"ok": True, **gauge}


class KimiExecutor(Executor):
    """STAGED — documented, not yet reality-checked. Flip `verified` to True only
    after an on-machine live-fire proof (discover binary, drive headless, read the
    `/usage` gauge) — exactly what was done for Codex.

    Documented (UNVERIFIED) shape, for the future reality-check to confirm:
      - headless : Moonshot Kimi CLI (`kimi`) — exec/non-interactive mode TBD
      - usage    : `/usage` in-CLI, or the community `kimi-code-usage` MCP server
      - windows  : subscription coding plan, 5h / weekly (Codex-like, refilling)
    """
    name = "kimi"
    verified = False
    _CANDIDATES = ("kimi", "kimi-cli", "kimi-code", "kimicode")

    def available(self):
        if any(which(c) for c in self._CANDIDATES):
            return True
        home = os.path.expanduser("~")
        return any(os.path.isdir(os.path.join(home, d)) for d in (".kimi", ".moonshot"))

    def read_remaining(self):
        raise ExecutorUnverified(
            "Kimi adapter is documented but not yet reality-checked on this machine. "
            "Install Kimi, run the live-fire verification, then set verified=True.")


_REGISTRY = {"codex": CodexExecutor, "kimi": KimiExecutor}


def _configured_names():
    """Which executors the Owner enabled. `DRYDOCK_EXECUTORS='codex,kimi'` pins the
    set; otherwise all known executors are considered and auto-detected."""
    raw = os.environ.get("DRYDOCK_EXECUTORS")
    if raw:
        names = [n.strip().lower() for n in raw.split(",") if n.strip()]
        return [n for n in names if n in _REGISTRY]
    return list(_REGISTRY.keys())


def executors():
    return [_REGISTRY[n]() for n in _configured_names()]


def fleet_status():
    """The N-tank picture. Claude (the conductor) is noted separately — its own
    quota is not machine-readable, so it is human-tracked."""
    ex = [e.status() for e in executors()]
    return {
        "conductor": {"name": "claude",
                      "note": "conductor; own quota not machine-readable (human-tracked)"},
        "executors": ex,
        "usable": [e["name"] for e in ex if e["available"] and e["verified"]],
        "staged": [e["name"] for e in ex if e["available"] and not e["verified"]],
    }


def main():
    print(json.dumps(fleet_status(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
