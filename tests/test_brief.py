"""Brief-engine tests (owner-brief spec). The polarity under test is the
red-team's: every degenerate input must fail DOWNWARD (toward a lower rung or
an explicit unavailable), never upward toward false peace. Golden trees pin
each rung and each live-confirmed wrongful-ascent class.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import _drydock_common as common

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import brief  # noqa: E402

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
    (root / "sdd-plus" / "archive").mkdir(parents=True)
    (root / "sdd-plus" / "standards").mkdir(parents=True)
    (root / "sdd-plus" / "standards" / "engineering-standards.md").write_text(
        "# Standards\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (root / "PROJECT_CONTEXT.md").write_text("# ctx\nreal answers here\n", encoding="utf-8")
    return root


def packet(root, name, tasks=None, verification=None, brief_md=None):
    p = root / "sdd-plus" / "changes" / name
    p.mkdir(parents=True, exist_ok=True)
    (p / "brief.md").write_text(brief_md or (
        "# Brief\n\n## What this means for your product\n\n"
        f"After {name}, you can see your status. Second sentence is dropped.\n"
        "\n## User Need\n\nFallback text.\n"), encoding="utf-8")
    if tasks is not None:
        (p / "tasks.md").write_text(tasks, encoding="utf-8")
    if verification is not None:
        (p / "verification.md").write_text(verification, encoding="utf-8")
    return p


def archive(root, name, result="PASS. All good.\n", override=False, complete=True):
    a = root / "sdd-plus" / "archive" / name
    a.mkdir(parents=True)
    (a / "brief.md").write_text("# Brief\n\n## User Need\n\nShipped thing.\n", encoding="utf-8")
    if complete:
        (a / "tasks.md").write_text("- [x] all\n", encoding="utf-8")
        (a / "verification.md").write_text("# V\n\n## Result\n\n" + result, encoding="utf-8")
        (a / "decision-log.md").write_text(
            "# Decision Log\n\n## Decisions\n\n| a |\n"
            + ("\n## Override\n\n- gates waived\n" if override else ""), encoding="utf-8")
    return a


def item_by_name(f, name):
    return next(i for i in f["items"] if i["name"] == name)


# --- rung ascent requires positive evidence (live-confirmed classes) ---------
def test_missing_tasks_md_is_idea_not_claimed_done(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "bare")  # brief.md only — the hand-created-dir attack
    assert item_by_name(brief.facts(root), "bare")["rung"] == "idea"


def test_prose_tasks_without_checkboxes_is_idea(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "prose", tasks="We will do things soon.\n")
    assert item_by_name(brief.facts(root), "prose")["rung"] == "idea"


def test_pending_tasks_is_being_built(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "wip", tasks="- [x] a\n- [ ] b\n")
    it = item_by_name(brief.facts(root), "wip")
    assert it["rung"] == "being-built"
    assert it["counts"] == {"done": 1, "pending": 1}


def test_done_tasks_pending_verification_is_built_not_checked(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "done-unchecked", tasks="- [x] a\n",
           verification="## Result\n\nPending.\n")
    assert item_by_name(brief.facts(root), "done-unchecked")["rung"] == "built-not-checked"


def test_headingless_verification_cannot_ascend(tmp_path, state_dir):
    """Live-confirmed: free-form notes with no '## Result' heading read as
    'filled' in the completion-gate parser. Here they must refuse ascent."""
    root = make_project(tmp_path)
    packet(root, "headingless", tasks="- [x] a\n",
           verification="Will verify later, promise.\n")
    assert item_by_name(brief.facts(root), "headingless")["rung"] == "built-not-checked"


def test_not_verified_result_freezes_with_note_and_move(tmp_path, state_dir):
    """Live-confirmed worst polarity: a NOT VERIFIED verdict must never render
    as checked."""
    root = make_project(tmp_path)
    packet(root, "failed-check", tasks="- [x] a\n",
           verification="## Result\n\n**NOT VERIFIED.** 3 defects found.\n")
    it = item_by_name(brief.facts(root), "failed-check")
    assert it["rung"] == "built-not-checked"
    assert it["note"] == "record-not-pass"
    assert it["your_move"] == "review-not-pass"


def test_affirmative_pass_reaches_checked_recorded(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "passed", tasks="- [x] a\n",
           verification="## Result\n\nPASS. Verifier-confirmed on all claims.\n")
    it = item_by_name(brief.facts(root), "passed")
    assert it["rung"] == "checked-recorded"
    assert it["confirmed_here"] is False  # no verify-run event -> recorded claim only


def test_pass_with_open_questions_counts_as_pass(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "open-q", tasks="- [x] a\n",
           verification="## Result\n\nPASS WITH OPEN QUESTIONS: two notes.\n")
    assert item_by_name(brief.facts(root), "open-q")["rung"] == "checked-recorded"


def test_verify_run_event_with_matching_hash_confirms(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "confirmed", tasks="- [x] a\n",
           verification="## Result\n\nPASS.\n")
    cur = common.fingerprint_project(root)["confirmed"]["hash"]
    common.append_event(root, "brief", "verify", "verify-run",
                        extra={"packet": "confirmed", "hash": cur})
    assert item_by_name(brief.facts(root), "confirmed")["confirmed_here"] is True


def test_editing_after_verify_run_demotes_confirmation(tmp_path, state_dir):
    root = make_project(tmp_path)
    p = packet(root, "edited", tasks="- [x] a\n", verification="## Result\n\nPASS.\n")
    cur = common.fingerprint_project(root)["edited"]["hash"]
    common.append_event(root, "brief", "verify", "verify-run",
                        extra={"packet": "edited", "hash": cur})
    (p / "plan.md").write_text("changed after verification\n", encoding="utf-8")
    assert item_by_name(brief.facts(root), "edited")["confirmed_here"] is False


# --- archives ----------------------------------------------------------------
def test_clean_archive_is_done_documented(tmp_path, state_dir):
    root = make_project(tmp_path)
    archive(root, "2026-07-06-shipped-thing")
    it = item_by_name(brief.facts(root), "shipped-thing")
    assert it["rung"] == "done-documented" and it["date"] == "2026-07-06"


def test_forced_archive_is_distinguishable(tmp_path, state_dir):
    root = make_project(tmp_path)
    archive(root, "2026-07-06-forced-thing", override=True)
    it = item_by_name(brief.facts(root), "forced-thing")
    assert it["rung"] == "archived-exceptions"
    assert it["your_move"] == "review-exceptions"


def test_archive_with_non_pass_result_is_demoted(tmp_path, state_dir):
    root = make_project(tmp_path)
    archive(root, "2026-07-06-bad-result", result="NOT VERIFIED. nope.\n")
    assert item_by_name(brief.facts(root), "bad-result")["rung"] == "archived-exceptions"


def test_hand_moved_decoy_archive_gets_no_rung(tmp_path, state_dir):
    root = make_project(tmp_path)
    (root / "sdd-plus" / "archive" / "2026-07-06-decoy").mkdir(parents=True)
    assert item_by_name(brief.facts(root), "decoy")["rung"] == "incomplete-record"


# --- goal line ----------------------------------------------------------------
def test_goal_is_one_sentence_from_owner_line(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "goalful", tasks="- [ ] a\n")
    goal = item_by_name(brief.facts(root), "goalful")["goal"]
    assert goal == "After goalful, you can see your status."  # truncated at sentence


def test_goal_falls_back_to_user_need(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "legacy", tasks="- [ ] a\n",
           brief_md="# Brief\n\n## User Need\n\nOld-style packet need. More.\n")
    assert item_by_name(brief.facts(root), "legacy")["goal"] == "Old-style packet need."


# --- ledger-derived guardrail facts -------------------------------------------
def test_no_ledger_renders_unavailable_not_zero(tmp_path, state_dir):
    root = make_project(tmp_path)
    f = brief.facts(root)
    assert f["guardrails"] == {"history": "unavailable"}


def test_counts_and_coverage_bounds(tmp_path, state_dir):
    root = make_project(tmp_path)
    common.append_event(root, "session_orient", "session", "session")
    common.append_event(root, "packet_guard", "deny", "packet-deny:migration")
    common.append_event(root, "packet_guard", "warn", "packet-warn")  # not prevention
    gr = brief.facts(root)["guardrails"]
    assert gr["history"] == "ok" and gr["sessions"] == 1
    assert gr["paused_total"] == 1  # warn tier is orientation, never a "pause"


def test_young_ledger_with_old_archives_flags_missing_history(tmp_path, state_dir):
    root = make_project(tmp_path)
    archive(root, "2020-01-01-ancient-work")
    common.append_event(root, "git_safety", "deny", "git-deny")
    gr = brief.facts(root)["guardrails"]
    assert gr["older_history_not_visible"] is True


# --- engine states + status file ----------------------------------------------
def test_not_initialized_block(tmp_path, state_dir):
    assert brief.facts(None)["drydock"] == "not-initialized"


def test_write_status_deterministic_and_no_op_on_unchanged(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "wip", tasks="- [x] a\n- [ ] b\n")
    f = brief.facts(root)
    r1 = brief.write_status(root, f, "en")
    assert r1["written"] is True
    content1 = (root / "OWNER_STATUS.md").read_bytes()
    r2 = brief.write_status(root, brief.facts(root), None)  # lang from file comment
    assert r2 == {"written": False, "reason": "unchanged", "lang": "en"}
    assert (root / "OWNER_STATUS.md").read_bytes() == content1
    # deterministic bytes: rendering the same facts twice is identical
    assert brief.render_status(f, "en") == brief.render_status(f, "en")


def test_status_file_carries_staleness_anchor_fingerprint_and_lang(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "wip", tasks="- [ ] a\n")
    f = brief.facts(root)
    brief.write_status(root, f, "es")
    text = (root / "OWNER_STATUS.md").read_text(encoding="utf-8")
    assert f"fp={f['fingerprint']} lang=es" in text
    assert "Instantanea generada" in text          # frozen es labels
    assert text.splitlines()[0].startswith("# ")   # visible title+date first line
    # regeneration without --lang keeps the recorded language (no flip-flop churn)
    packet(root, "more", tasks="- [ ] b\n")
    r = brief.write_status(root, brief.facts(root), None)
    assert r["lang"] == "es"


def test_status_file_never_upgrades_claims(tmp_path, state_dir):
    root = make_project(tmp_path)
    packet(root, "failed-check", tasks="- [x] a\n",
           verification="## Result\n\nNOT VERIFIED. defects.\n")
    brief.write_status(root, brief.facts(root), "en")
    text = (root / "OWNER_STATUS.md").read_text(encoding="utf-8")
    assert "NOT yet checked" in text
    assert "verification record exists but it is not a pass" in text
    assert 'NOT "it\'s done"' in text


def test_record_verify_requires_genuine_gate_pass(tmp_path, state_dir):
    """Typing PASS into verification.md is not enough: the deterministic gate
    (sdd.py verify) still fails on the template TBDs, so no event is recorded."""
    root = make_project(tmp_path)
    scripts = root / "scripts"
    scripts.mkdir()
    import shutil
    shutil.copy(REPO / "scripts" / "sdd.py", scripts / "sdd.py")
    p = packet(root, "cheater", tasks="- [x] a\n- [ ] TBD\n",
               verification="## Result\n\nPASS.\n")
    (p / "plan.md").write_text("# Plan\n\nreal\n", encoding="utf-8")
    (p / "decision-log.md").write_text("# D\n\nreal\n", encoding="utf-8")
    r = brief.record_verify(root, "cheater")
    assert r["recorded"] is False and r["reason"] == "gate-failed"
    assert common.read_events(root) is None  # nothing was written


def test_record_verify_records_on_real_pass(tmp_path, state_dir):
    root = make_project(tmp_path)
    scripts = root / "scripts"
    scripts.mkdir()
    import shutil
    shutil.copy(REPO / "scripts" / "sdd.py", scripts / "sdd.py")
    p = packet(root, "honest", tasks="- [x] a\n",
               verification="# V\n\n## Result\n\nPASS. done.\n")
    (p / "plan.md").write_text("# Plan\n\nreal\n", encoding="utf-8")
    (p / "decision-log.md").write_text("# D\n\nreal\n", encoding="utf-8")
    r = brief.record_verify(root, "honest")
    assert r["recorded"] is True
    assert item_by_name(brief.facts(root), "honest")["confirmed_here"] is True


def test_cli_smoke_exit_zero_and_valid_json(tmp_path, state_dir):
    """The command contract: always exit 0, always a parseable block —
    including outside any Drydock project."""
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "brief.py")],
                          cwd=str(tmp_path), capture_output=True, timeout=30)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["drydock"] == "not-initialized"


def test_decoy_common_module_is_not_imported(tmp_path, state_dir):
    """Import anchoring: a hostile repo planting _drydock_common.py at its root
    (and in cwd) must not be executed by the engine (red-teamed RCE class)."""
    root = make_project(tmp_path)
    evil = "import sys\nsys.stderr.write('PWNED')\nraise SystemExit(99)\n"
    (root / "_drydock_common.py").write_text(evil, encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "_drydock_common.py").write_text(evil, encoding="utf-8")
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "brief.py")],
                          cwd=str(root), capture_output=True, timeout=30)
    assert proc.returncode == 0
    assert b"PWNED" not in proc.stderr
    assert json.loads(proc.stdout)["drydock"] == "ok"
