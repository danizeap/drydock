"""Event-ledger contract tests (owner-brief spec, 'Best-effort, category-only
event ledger'). The load-bearing invariants: appends can never change a guard's
verdict OR its delivered bytes; categories are validated at the sink; probes are
excluded; hostile ledgers degrade to absence (None), never to a lie or a crash.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import _drydock_common as common

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
SID = "session-abcdef123456"


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    d = tmp_path / "state"
    d.mkdir()
    monkeypatch.setattr(common, "_state_dir", lambda: d)
    monkeypatch.setattr(common, "_candidate_state_bases", lambda: [])
    monkeypatch.delenv("DRYDOCK_PROBE", raising=False)
    return d


def make_project(root):
    (root / "sdd-plus" / "protocols").mkdir(parents=True)
    (root / "sdd-plus" / "changes").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    return root


def journal(root):
    return common.ledger_path(root)


# --- append basics -----------------------------------------------------------
def test_append_creates_with_birth_line_and_event(tmp_path, state_dir):
    root = make_project(tmp_path)
    common.append_event(root, "git_safety", "deny", "git-deny")
    lines = journal(root).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["category"] == "ledger-created"
    evt = json.loads(lines[1])
    assert evt["category"] == "git-deny" and evt["hook"] == "git_safety"
    import re
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", evt["ts"])  # date-only, never clock time


def test_unknown_category_is_coerced_never_verbatim(tmp_path, state_dir):
    root = make_project(tmp_path)
    common.append_event(root, "git_safety", "deny", "C:/secret/path/.env leaked")
    text = journal(root).read_text(encoding="utf-8")
    assert "secret" not in text and ".env" not in text
    assert json.loads(text.splitlines()[-1])["category"] == "other"


def test_extra_fields_validated_at_sink(tmp_path, state_dir):
    root = make_project(tmp_path)
    common.append_event(root, "brief", "verify", "verify-run",
                        extra={"packet": "my-change", "hash": "a" * 16,
                               "evil": "x", "path": "/etc/passwd"})
    common.append_event(root, "brief", "verify", "verify-run",
                        extra={"packet": "NOT KEBAB!!", "hash": "zz"})
    lines = journal(root).read_text(encoding="utf-8").splitlines()
    ok = json.loads(lines[1])
    assert ok["packet"] == "my-change" and ok["hash"] == "a" * 16
    assert "evil" not in ok and "path" not in ok
    bad = json.loads(lines[2])
    assert "packet" not in bad and "hash" not in bad


def test_probe_env_makes_append_a_noop(tmp_path, state_dir, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setenv("DRYDOCK_PROBE", "1")
    common.append_event(root, "git_safety", "deny", "git-deny")
    assert not journal(root).exists()


def test_append_swallows_unwritable_state_dir(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(common, "_state_dir", lambda: None)
    common.append_event(root, "git_safety", "deny", "git-deny")  # must not raise


def test_symlinked_journal_refused(tmp_path, state_dir):
    root = make_project(tmp_path)
    victim = tmp_path / "victim.txt"
    victim.write_text("private\n", encoding="utf-8")
    try:
        journal(root).symlink_to(victim)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    common.append_event(root, "git_safety", "deny", "git-deny")
    assert victim.read_text(encoding="utf-8") == "private\n"  # never appended into


def test_rotation_over_cap(tmp_path, state_dir, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(common, "_MAX_LEDGER_BYTES", 200)
    for _ in range(10):
        common.append_event(root, "git_safety", "deny", "git-deny")
    rotated = Path(str(journal(root)) + ".1")
    assert rotated.exists()
    # post-rotation journal restarts with a fresh birth line
    first = json.loads(journal(root).read_text(encoding="utf-8").splitlines()[0])
    assert first["category"] == "ledger-created"


# --- reader discipline -------------------------------------------------------
def test_read_events_missing_is_none_not_empty(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert common.read_events(root) is None  # absence, distinguishable from zero


def test_read_events_roundtrip_and_torn_lines(tmp_path, state_dir):
    root = make_project(tmp_path)
    common.append_event(root, "git_safety", "deny", "git-deny")
    with open(journal(root), "a", encoding="utf-8") as f:
        f.write('{"ts": "2026-07-07", "cat')          # torn line
        f.write("\nnot json at all\n")
        f.write('{"no_ts": true}\n')                   # schema-less
    events = common.read_events(root)
    assert [e["category"] for e in events] == ["ledger-created", "git-deny"]


def test_read_events_skips_giant_lines_and_binary(tmp_path, state_dir):
    root = make_project(tmp_path)
    common.append_event(root, "git_safety", "deny", "git-deny")
    with open(journal(root), "ab") as f:
        f.write(b'{"ts":"2026-07-07","category":"' + b"A" * 4096 + b'"}\n')
        f.write(b"\xff\xfe\x00garbage\n")
    events = common.read_events(root)
    assert len(events) == 2  # birth + real; giant and binary lines skipped


def test_read_events_symlink_refused(tmp_path, state_dir):
    root = make_project(tmp_path)
    victim = tmp_path / "victim.ndjson"
    victim.write_text('{"ts":"2026-07-07","category":"git-deny"}\n', encoding="utf-8")
    try:
        journal(root).symlink_to(victim)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert common.read_events(root) is None  # symlink -> treated as unreadable


def test_read_events_tail_window_bounds_growth(tmp_path, state_dir, monkeypatch):
    root = make_project(tmp_path)
    common.append_event(root, "git_safety", "deny", "git-deny")
    with open(journal(root), "a", encoding="utf-8") as f:
        for i in range(5000):
            f.write(json.dumps({"ts": "2026-07-07", "hook": "x", "action": "deny",
                                "category": "git-deny"}) + "\n")
    events = common.read_events(root)
    assert 0 < len(events) <= common._MAX_EVENTS


# --- verdict-delivery independence (all four writers) -------------------------
# First verifier pass proved the original version of these tests VACUOUS: the
# payload cwd had no Drydock markers (append path never reached) and "broken"
# env bases fell back to writable candidates. The rebuilt tests are structurally
# anti-vacuous: the HEALTHY run must produce a journal line (proving the append
# path executed), and the BROKEN run plants a DIRECTORY at the journal's own
# path — unwritable regardless of base fallback (lstat/S_ISREG refusal).
def _run_hook(script, payload, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(HOOKS / script)],
                          input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, timeout=15, env=env)


def _subprocess_ledger(tmp_path, root):
    """(env, journal_path) for a subprocess whose state dir is tmp-local; the
    journal path is computed exactly as the hook process will compute it."""
    import hashlib
    base = tmp_path / "appdata"
    base.mkdir(exist_ok=True)
    env = {"LOCALAPPDATA": str(base), "XDG_CACHE_HOME": str(base)}
    found = common.find_drydock_root(Path(str(root)), None)
    digest = hashlib.sha256(os.path.normcase(str(found)).encode("utf-8", "replace")).hexdigest()[:16]
    return env, base / "drydock" / f"drydock-journal-{digest}.ndjson"


@pytest.mark.parametrize("script,payload_fn,expect,category", [
    ("git_safety.py",
     lambda root: {"tool_name": "Bash", "cwd": str(root), "session_id": SID,
                   "tool_input": {"command": "git reset --hard"}},
     b"git-safety", "git-deny"),
    ("protect_secrets.py",
     lambda root: {"tool_name": "Write", "cwd": str(root), "session_id": SID,
                   "tool_input": {"file_path": str(root / ".env")}},
     b"secrets", "secrets-deny"),
])
def test_verdict_delivery_identical_healthy_vs_broken_ledger(tmp_path, script, payload_fn,
                                                             expect, category):
    root = make_project(tmp_path / "proj")
    payload = payload_fn(root)
    env, journal = _subprocess_ledger(tmp_path, root)

    healthy = _run_hook(script, payload, env)
    assert healthy.returncode == 2 and expect in healthy.stderr
    # anti-vacuous guard: the healthy run MUST have reached the append path
    assert journal.is_file(), "append path was not exercised — test would be vacuous"
    assert category in journal.read_text(encoding="utf-8")

    journal.unlink()
    journal.mkdir()  # a directory at the journal's own path: unwritable, no fallback
    hurt = _run_hook(script, payload, env)
    assert not any(journal.iterdir())  # nothing was written anywhere into it
    assert hurt.returncode == healthy.returncode == 2
    assert hurt.stdout == healthy.stdout
    assert hurt.stderr == healthy.stderr


def test_packet_guard_deny_json_identical_healthy_vs_broken_ledger(tmp_path):
    root = make_project(tmp_path / "proj")
    payload = {"tool_name": "Write", "cwd": str(root), "session_id": SID,
               "tool_input": {"file_path": str(root / "migrations" / "0001.sql")}}
    env, journal = _subprocess_ledger(tmp_path, root)

    healthy = _run_hook("packet_guard.py", payload, env)
    assert healthy.returncode == 0
    assert b'"deny"' in healthy.stdout
    assert journal.is_file() and "packet-deny:migration" in journal.read_text(encoding="utf-8")

    journal.unlink()
    journal.mkdir()
    hurt = _run_hook("packet_guard.py", payload, env)
    assert hurt.returncode == 0
    assert hurt.stdout == healthy.stdout
    assert hurt.stderr == healthy.stderr


def test_completion_gate_nudge_survives_pathological_ledger(tmp_path, state_dir, monkeypatch):
    """Even a ledger layer that RAISES cannot suppress or alter the nudge —
    append_event's swallow-all is the last line of defense and must hold."""
    import completion_gate as cg
    root = make_project(tmp_path)
    p = root / "sdd-plus" / "changes" / "alpha"
    p.mkdir(parents=True)
    (p / "tasks.md").write_text("- [x] build\n", encoding="utf-8")
    (p / "verification.md").write_text("## Result\n\nPending.\n", encoding="utf-8")
    common.write_state(common.state_path(SID), common.new_state(SID, {}))

    def boom(_root):
        raise RuntimeError("pathological ledger layer")
    monkeypatch.setattr(common, "ledger_path", boom)
    assert cg.run({"cwd": str(root), "session_id": SID}) == "alpha"
    # and the nudge was durably persisted despite the ledger failure
    state = common.read_state(common.state_path(SID), SID)
    assert state["nudged"] == ["alpha"]


def test_orientation_probe_leaves_ledger_byte_identical(tmp_path, state_dir):
    """A full liveness probe pass must fabricate zero events (red-teamed:
    otherwise ~2 synthetic denies per session pollute the Owner's history)."""
    import session_orient as so
    root = make_project(tmp_path)
    common.append_event(root, "git_safety", "deny", "git-deny")  # one real event
    before = journal(root).read_bytes()
    for (_label, script, block, benign, expect) in so._PROBES:
        verdict = so.probe_guard(HOOKS, script, block, benign, expect)
        assert verdict == "live"  # the env var must NOT fail the guard open
    assert journal(root).read_bytes() == before


def test_completion_gate_nudge_appends_event(tmp_path, state_dir):
    import completion_gate as cg
    root = make_project(tmp_path)
    p = root / "sdd-plus" / "changes" / "alpha"
    p.mkdir(parents=True)
    (p / "tasks.md").write_text("- [x] build\n", encoding="utf-8")
    (p / "verification.md").write_text("## Result\n\nPending.\n", encoding="utf-8")
    common.write_state(common.state_path(SID), common.new_state(SID, {}))
    assert cg.run({"cwd": str(root), "session_id": SID}) == "alpha"
    cats = [e["category"] for e in common.read_events(root)]
    assert "verify-nudge" in cats
