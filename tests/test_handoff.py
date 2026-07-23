"""Tests for the HANDOFF relay (`scripts/conductor/handoff.py`).

Real git repos in temp dirs; the executor fleet is monkeypatched for
determinism (no quota). Read-only gathering + HANDOFF.md render/write/read.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import handoff as hf  # noqa: E402
from conductor import executors as ex  # noqa: E402


def _g(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo(path):
    _g(["init"], path)
    _g(["config", "user.email", "t@example.com"], path)
    _g(["config", "user.name", "Test"], path)
    with open(os.path.join(path, "seed.txt"), "w") as f:
        f.write("seed\n")
    _g(["add", "-A"], path)
    _g(["commit", "-m", "seed"], path)


_FAKE_FLEET = {
    "conductor": {"name": "claude"},
    "executors": [{"name": "codex", "available": True, "verified": True,
                   "fuel": {"ok": True, "remaining_percent": 90, "resets_in_hours": 100}}],
    "usable": ["codex"], "staged": [],
}


# ---- fleet recommendation (pure) ----
def test_recommendation_prefers_near_reset():
    fleet = {"executors": [
        {"name": "codex", "available": True, "verified": True,
         "fuel": {"ok": True, "remaining_percent": 95, "resets_in_hours": 120}},
        {"name": "kimi", "available": True, "verified": True,
         "fuel": {"ok": True, "remaining_percent": 40, "resets_in_hours": 4}},
    ]}
    joined = "\n".join(hf.fleet_recommendation(fleet))
    assert "prefer spending 'kimi'" in joined  # closest to reset


def test_recommendation_flags_low_tank():
    fleet = {"executors": [{"name": "codex", "available": True, "verified": True,
                            "fuel": {"ok": True, "remaining_percent": 8, "resets_in_hours": 50}}]}
    assert "LOW" in "\n".join(hf.fleet_recommendation(fleet))


def test_recommendation_claude_solo():
    joined = "\n".join(hf.fleet_recommendation({"executors": []}))
    assert "human-tracked" in joined and "Claude-solo" in joined


# ---- gather / render / write / read ----
def test_gather_render_write_read(monkeypatch, tmp_path):
    repo = str(tmp_path)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    pkt = os.path.join(repo, "sdd-plus", "changes", "my-pkt")
    os.makedirs(pkt)
    with open(os.path.join(pkt, "tasks.md"), "w", encoding="utf-8") as f:
        f.write("- [ ] unfinished\n")           # marks it genuinely IN-FLIGHT
    monkeypatch.setattr(ex, "fleet_status", lambda: _FAKE_FLEET)
    state = hf.gather_state()
    assert state["branch"] and state["branch"] != "(unknown)"
    assert "my-pkt" in state["packets"] and "my-pkt" in state["in_flight_packets"]
    path = hf.write_handoff("do the thing", "some notes",
                            path=os.path.join(repo, "HANDOFF.md"), stamp="2026-07-23 00:00Z")
    content = hf.read_handoff(path)
    assert "# HANDOFF" in content
    assert "do the thing" in content and "some notes" in content
    assert "codex: 90%" in content and "my-pkt" in content


def test_finished_packet_is_not_in_flight(monkeypatch, tmp_path):
    # "sitting in sdd-plus/changes" != "in flight" — a finished packet is listed
    # but must not clutter the handoff's in-flight line (field-report 6.5).
    repo = str(tmp_path)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    done = os.path.join(repo, "sdd-plus", "changes", "done-pkt")
    os.makedirs(done)
    with open(os.path.join(done, "tasks.md"), "w", encoding="utf-8") as f:
        f.write("- [x] all done\n")
    with open(os.path.join(done, "verification.md"), "w", encoding="utf-8") as f:
        f.write("## Result\n\nVERIFIED.\n")
    packets, in_flight = hf._packets()
    assert "done-pkt" in packets and "done-pkt" not in in_flight


def test_read_missing_handoff(tmp_path):
    assert hf.read_handoff(os.path.join(str(tmp_path), "nope.md")) is None


# ---- codex worktree detection ----
def test_codex_worktree_detected(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    monkeypatch.chdir(repo)
    wt = str(tmp_path / "wt")
    _g(["worktree", "add", wt, "-b", "codex/test", "HEAD"], repo)
    try:
        trees = hf._codex_worktrees()
        assert any("codex/test" in t.get("branch", "") for t in trees)
    finally:
        _g(["worktree", "remove", "--force", wt], repo)
