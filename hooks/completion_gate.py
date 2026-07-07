#!/usr/bin/env python3
"""Stop hook: 'done' should mean verified done.

When — and only when — a change packet that looks CLAIMED-DONE (implementation
tasks finished) still has `verification.md` at 'Pending.' AND its content changed
during this session, block the stop ONCE for that packet (session cap 3) with a
precise nudge. Silent in every other case.

Loop safety is the whole game (the platform gives Stop no loop-prevention flag):
- Fail direction is ALWAYS silent-allow. A false block/loop is catastrophic for
  adoption; a missed nudge costs nothing — the archive gates remain the hard
  deterministic backstop. This is the OPPOSITE polarity from the git/secrets guards.
- The nudge is persisted (nudged ledger, atomic write) BEFORE the block is spoken;
  if the write fails for any reason, nothing is emitted — a persistence failure
  degrades to silence, never repetition.
- Discovery + fingerprinting come from the shared `_drydock_common` module, so the
  Stop gate and the SessionStart stamp can never drift apart.
"""
import json
import sys
from pathlib import Path

from _drydock_common import (STATE_SCHEMA, find_drydock_root, plugin_root_from_env,
                             sanitize_sid, state_path, read_state, write_state,
                             new_state, fingerprint_project)

_MAX_NUDGES = 3


def run(data):
    """Return a packet name to nudge about, or None to stay silent. Never raises
    for control flow (caller wraps in except BaseException)."""
    if data.get("stop_hook_active"):
        return None  # defensive: honor an undocumented loop flag if present
    cwd = data.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        return None
    import os
    if not os.path.isabs(cwd) or not os.path.isdir(cwd):
        return None
    sid = sanitize_sid(data.get("session_id"))
    if sid is None:
        return None
    root = find_drydock_root(Path(cwd), plugin_root_from_env())
    if root is None:
        return None
    path = state_path(sid)
    if path is None:
        return None
    current = fingerprint_project(root)
    state = read_state(path, sid)
    if state is None:
        # Self-heal: orient never ran / temp cleaned / corrupt. Stamp a baseline
        # now (this turn's in-flight work is missed once) and stay silent, so
        # every later turn of the session is covered.
        write_state(path, new_state(sid, current))
        return None

    baseline = state.get("fingerprints", {})
    nudged = [n for n in state.get("nudged", []) if isinstance(n, str)]
    if len(nudged) >= _MAX_NUDGES:
        return None

    for name in sorted(current):
        if name in nudged:
            continue
        st = current[name]
        base = baseline.get(name)
        changed = (base is None) or (base.get("hash") != st.get("hash"))
        if st.get("verification_pending") and st.get("claimed_done") and changed:
            # persist the nudge BEFORE speaking; keep the session-start baseline
            # so later work on other packets still compares against session start.
            updated = {"v": STATE_SCHEMA, "session_id": sid,
                       "fingerprints": baseline, "nudged": nudged + [name]}
            return name if write_state(path, updated) else None
    return None


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            return 0
        name = run(data)
        if name:
            reason = (
                f"Drydock completion check: files under sdd-plus/changes/{name} changed this "
                f"session and the packet's tasks look complete, but its verification.md is still "
                f"'Pending.'. If you did this work, run /drydock:verify {name} before calling it "
                f"done. If the Owner asked to defer verification, say so explicitly and stop. If "
                f"you did not make these changes, do not modify the packet — flag it to the Owner."
            )
            print(json.dumps({"decision": "block", "reason": reason}))
    except BaseException:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
