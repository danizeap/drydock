"""Two-brain plan negotiation (`scripts/conductor/negotiate.py`): the read-only
critique round + the bounded-loop control that keeps Fable and 5.6 from arguing
forever. `discover_core` is monkeypatched to the fake Codex — no quota, no network.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import codex_bridge as cb  # noqa: E402
from conductor import negotiate as neg  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


# ---- one critique round: the delegation plumbing ----

def test_critique_round_runs_the_delegation(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(neg.cb, "discover_core", lambda *a, **k: FAKE)
    out = neg.critique_plan("Add a /health endpoint. Steps: 1. route 2. test.", "heavy")
    assert out["ok"] is True
    assert out["round"] == 1 and out["cap"] == neg.DEFAULT_CAP
    assert out["gauge"]["remaining_percent"] == 95
    assert out["route"]["model"] == cb.FLAGSHIP           # heavy + full fuel


def test_light_round_routes_workhorse(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(neg.cb, "discover_core", lambda *a, **k: FAKE)
    out = neg.critique_plan("tiny plan", "light")
    assert out["ok"] is True and out["route"]["model"] == cb.WORKHORSE


def test_empty_plan_refused(monkeypatch):
    monkeypatch.setattr(neg.cb, "discover_core", lambda *a, **k: FAKE)
    out = neg.critique_plan("   \n  ", "heavy")
    assert out["ok"] is False and out["stage"] == "empty_plan"


def test_secret_bearing_plan_refused_before_sending(monkeypatch):
    spawned = []
    monkeypatch.setattr(neg.cb, "discover_core", lambda *a, **k: spawned.append(1) or FAKE)
    out = neg.critique_plan("deploy with OPENAI_KEY = 'sk-" + "a" * 24 + "'", "heavy")
    assert out["ok"] is False and out["stage"] == "secret_content"
    assert spawned == []                                  # refused before discovery/spawn


def test_no_core(monkeypatch):
    monkeypatch.setattr(neg.cb, "discover_core", lambda *a, **k: None)
    out = neg.critique_plan("real plan text", "heavy")
    assert out["ok"] is False and out["stage"] == "discover"


def test_prompt_frames_plan_as_data_and_names_the_round():
    p = neg._build_prompt("PLAN BODY", round_num=1, cap=2)
    assert "PEER" in p and "DATA" in p and "round 1 of at most 2" in p
    assert "PLAN BODY" in p


def test_prompt_forces_a_decision_on_the_final_round():
    p = neg._build_prompt("x", round_num=2, cap=2)
    assert "FINAL round" in p and "resolve to a decision" in p


def test_prompt_fence_escalates_if_the_plan_carries_the_marker():
    p = neg._build_prompt("see DRYDOCK_FILE_BOUNDARY here", round_num=1, cap=2)
    assert "DRYDOCK_FILE_BOUNDARY_1" in p                 # content can't close its own fence


# ---- the bounded loop: the safety property ----

def test_loop_stops_when_both_agree():
    c = {"converged": True, "blocking_concerns": []}
    r = neg.loop_should_continue(c, round_num=1, cap=2)
    assert r["continue"] is False and "agree" in r["reason"]


def test_loop_continues_on_blocking_concerns():
    c = {"converged": False, "blocking_concerns": [{"issue": "no rollback", "why": "risky"}]}
    r = neg.loop_should_continue(c, round_num=1, cap=2)
    assert r["continue"] is True and "1 blocking" in r["reason"]


def test_loop_always_stops_at_the_cap():
    """The hard safety stop: no matter how many concerns remain, the cap ends it."""
    c = {"converged": False, "blocking_concerns": [{"issue": "x", "why": "y"}] * 9}
    r = neg.loop_should_continue(c, round_num=2, cap=2)
    assert r["continue"] is False and "cap" in r["reason"]


def test_loop_distrusts_converged_true_with_blocking_concerns():
    """A converged flag that still lists blockers is a contradiction — don't trust
    it; keep negotiating (until the cap) rather than paper over the concern."""
    c = {"converged": True, "blocking_concerns": [{"issue": "auth unclear", "why": "z"}]}
    r = neg.loop_should_continue(c, round_num=1, cap=2)
    assert r["continue"] is True


def test_loop_handles_a_missing_critique():
    r = neg.loop_should_continue(None, round_num=1, cap=2)
    assert r["continue"] is False and "pilot decides" in r["reason"]
