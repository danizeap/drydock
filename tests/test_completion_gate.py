"""Behavioral tests for the Stop-hook completion gate + the shared state channel
(completion-gate spec). Covers the red-teamed invariants: no loop (INV-A), never
breaks a session (INV-B), no false nudge (INV-C), and state-file safety (INV-E).
"""
import io

import pytest

import _drydock_common as common
import completion_gate as cg
import session_orient as so

SID = "session-abcdef123456"


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    d = tmp_path / "state"
    d.mkdir()
    monkeypatch.setattr(common, "_state_dir", lambda: d)
    return d


def make_project(root, packet="demo-pkt", tasks_done=False, verif_pending=True):
    (root / "sdd-plus" / "protocols").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    pdir = root / "sdd-plus" / "changes" / packet
    pdir.mkdir(parents=True)
    pdir.joinpath("tasks.md").write_text(
        "- [x] a\n- [x] b\n- [x] c\n" if tasks_done else "- [x] a\n- [ ] b\n- [ ] c\n",
        encoding="utf-8")
    pdir.joinpath("verification.md").write_text(
        "## Result\n\n" + ("Pending.\n" if verif_pending else "PASS.\n"), encoding="utf-8")
    return root


def _pkt(root, packet="demo-pkt"):
    return root / "sdd-plus" / "changes" / packet


def stamp(root):
    common.write_state(common.state_path(SID), common.new_state(SID, common.fingerprint_project(root)))


def gate(root):
    return cg.run({"cwd": str(root), "session_id": SID})


# --- the core behavior -----------------------------------------------------
def test_nudges_once_then_silent(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=False)   # work-in-progress at start
    stamp(root)                                        # baseline
    _pkt(root).joinpath("tasks.md").write_text("- [x] a\n- [x] b\n- [x] c\n", encoding="utf-8")  # now claimed-done
    assert gate(root) == "demo-pkt"                    # nudged once
    assert gate(root) is None                          # once per session: silent thereafter


def test_silent_pure_conversation(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)     # already done+pending at start
    stamp(root)
    assert gate(root) is None                          # nothing changed this session


def test_silent_when_tasks_incomplete_preserves_budget(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=False)
    stamp(root)
    _pkt(root).joinpath("plan.md").write_text("more planning\n", encoding="utf-8")  # work, but not done
    assert gate(root) is None                          # not claimed-done -> no premature nudge


def test_silent_when_verification_filled(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=False)
    stamp(root)
    _pkt(root).joinpath("tasks.md").write_text("- [x] a\n- [x] b\n- [x] c\n", encoding="utf-8")
    _pkt(root).joinpath("verification.md").write_text("## Result\n\nPASS.\n", encoding="utf-8")
    assert gate(root) is None                          # verification no longer Pending


def test_verification_only_task_counts_as_claimed_done(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=False)
    stamp(root)
    _pkt(root).joinpath("tasks.md").write_text("- [x] a\n- [x] b\n- [ ] Run verification.\n", encoding="utf-8")
    assert gate(root) == "demo-pkt"                    # sole remaining unchecked is the verify task


def test_deleting_verification_does_not_evade(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=False)
    stamp(root)
    _pkt(root).joinpath("tasks.md").write_text("- [x] a\n- [x] b\n- [x] c\n", encoding="utf-8")
    _pkt(root).joinpath("verification.md").unlink()    # missing == pending
    assert gate(root) == "demo-pkt"


# --- self-heal & loop-safety -----------------------------------------------
def test_self_heal_when_no_state_file(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)     # done+pending but orient never stamped
    assert gate(root) is None                          # stamp a baseline, stay silent this turn
    assert common.read_state(common.state_path(SID), SID) is not None


def test_session_cap_stops_nudging(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    common.write_state(common.state_path(SID), {"v": common.STATE_SCHEMA, "session_id": SID,
                                                "fingerprints": {}, "nudged": ["a", "b", "c"]})
    assert gate(root) is None                          # cap (3) already reached


def test_merge_preserves_nudged_on_compact(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    so._stamp_session_state(root, {"session_id": SID, "source": "startup"})
    p = common.state_path(SID)
    s = common.read_state(p, SID); s["nudged"] = ["demo-pkt"]; common.write_state(p, s)
    so._stamp_session_state(root, {"session_id": SID, "source": "compact"})  # auto-compact must not re-arm
    assert common.read_state(p, SID)["nudged"] == ["demo-pkt"]


def test_startup_resets_baseline(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    so._stamp_session_state(root, {"session_id": SID, "source": "startup"})
    p = common.state_path(SID)
    s = common.read_state(p, SID); s["nudged"] = ["x"]; common.write_state(p, s)
    so._stamp_session_state(root, {"session_id": SID, "source": "startup"})  # genuine new session
    assert common.read_state(p, SID)["nudged"] == []


# --- untrusted input & never-break -----------------------------------------
def test_untrusted_session_id_is_silent(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    assert cg.run({"cwd": str(root), "session_id": "short"}) is None   # < 8 chars
    assert cg.run({"cwd": str(root)}) is None                          # missing


def test_stop_hook_active_short_circuits(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    stamp(root)
    _pkt(root).joinpath("tasks.md").write_text("- [x] a\n", encoding="utf-8")
    assert cg.run({"cwd": str(root), "session_id": SID, "stop_hook_active": True}) is None


def test_non_drydock_is_silent(tmp_path, state_dir):
    assert cg.run({"cwd": str(tmp_path), "session_id": SID}) is None


def test_main_exits_zero_on_bad_stdin(monkeypatch):
    monkeypatch.setattr(cg.sys, "stdin", io.StringIO("not json"))
    assert cg.main() == 0
    monkeypatch.setattr(cg.sys, "stdin", io.StringIO(""))
    assert cg.main() == 0


# --- state-file safety -----------------------------------------------------
def test_oversized_state_treated_as_missing(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    common.state_path(SID).write_text("x" * (65 * 1024), encoding="utf-8")
    assert gate(root) is None                          # oversized -> missing -> self-heal, no crash


def test_corrupt_state_treated_as_missing(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    common.state_path(SID).write_text("{ not valid json", encoding="utf-8")
    assert gate(root) is None


def test_state_filename_is_hashed_no_traversal(state_dir):
    p = common.state_path("../../../etc/pwned-abcdef")
    assert p is not None and ".." not in p.name and p.name.startswith("drydock-state-")


def test_foreign_session_id_in_file_is_rejected(tmp_path, state_dir):
    root = make_project(tmp_path, tasks_done=True)
    common.write_state(common.state_path(SID), {"v": common.STATE_SCHEMA, "session_id": "someone-else",
                                                "fingerprints": {}, "nudged": []})
    assert common.read_state(common.state_path(SID), SID) is None  # session_id mismatch -> missing
