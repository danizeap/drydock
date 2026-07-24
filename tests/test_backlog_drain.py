"""The backlog drain (0.12.1): read-only `triage` bucketing and the honest
`archive --abandon` disposition. The 48-packet backlog is abandoned MID-lifecycle,
so draining is neither archive-them-all nor fabricate-a-pass — triage names the
per-packet next action and abandon records the ABSENCE of a verification.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sdd  # noqa: E402

SDD = os.path.join(ROOT, "scripts", "sdd.py")

COMPLETE = {
    "brief.md": "# Brief\nreal\n", "plan.md": "# Plan\nreal\n",
    "tasks.md": "# Tasks\n- [x] done\n", "decision-log.md": "# Decision Log\nreal\n",
    "verification.md": "# Verification\n## Result\nPASS. green.\n",
}


def _root(tmp_path):
    (tmp_path / "sdd-plus" / "standards").mkdir(parents=True)
    (tmp_path / "sdd-plus" / "standards" / "e.md").write_text("x", encoding="utf-8")
    (tmp_path / "sdd-plus" / "specs" / "capabilities").mkdir(parents=True)
    (tmp_path / "sdd-plus" / "changes").mkdir(parents=True)
    return tmp_path


def _pkt(root, name, files=None, delta=None, living=None):
    ch = root / "sdd-plus" / "changes" / name
    (ch / "specs").mkdir(parents=True)
    for n, c in (files or COMPLETE).items():
        (ch / n).write_text(c, encoding="utf-8")
    if delta is not None:
        (ch / "specs" / "demo-cap.md").write_text(delta, encoding="utf-8")
    if living is not None:
        (root / "sdd-plus" / "specs" / "capabilities" / "demo-cap.md").write_text(
            living, encoding="utf-8")
    return ch


def _run(root, *args):
    return subprocess.run([sys.executable, SDD, *args], cwd=str(root),
                          capture_output=True, text=True)


# ---- triage bucketing ----

def test_classify_buckets_each_state(tmp_path):
    root = _root(tmp_path)
    caps = root / "sdd-plus" / "specs" / "capabilities"
    ready = _pkt(root, "ready",
                 delta="Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: A\nSHALL.\n",
                 living="# Capability: demo-cap\n\n## Requirements\n\n### Requirement: A\nSHALL.\n")
    unsynced = _pkt(root, "unsynced",
                    delta="Capability: demo-cap2\n\n## ADDED Requirements\n\n### Requirement: B\nSHALL.\n")
    inprog = _pkt(root, "inprog", files=dict(COMPLETE, **{"tasks.md": "# T\n- [ ] todo\n"}))
    unverif = _pkt(root, "unverif",
                   files=dict(COMPLETE, **{"verification.md": "# V\n## Result\nPending.\n"}))
    assert sdd._classify_packet(ready, caps)[0] == "ARCHIVE-READY"
    assert sdd._classify_packet(unsynced, caps)[0] == "NEEDS-SYNC"
    assert sdd._classify_packet(inprog, caps)[0] == "IN-PROGRESS"
    assert sdd._classify_packet(unverif, caps)[0] == "CLAIMED-DONE-UNVERIFIED"


def test_classify_non_canonical_is_needs_sync(tmp_path):
    root = _root(tmp_path)
    ch = _pkt(root, "nc",
              delta="Capability: demo-cap\n\n## ADDED Requirements\n\n### R1 — thing\nSHALL.\n")
    bucket, detail = sdd._classify_packet(ch, root / "sdd-plus" / "specs" / "capabilities")
    assert bucket == "NEEDS-SYNC" and "grammar" in detail


def test_classify_missing_file_is_in_progress_not_a_crash(tmp_path):
    """The messiest backlog packets are missing files; they must bucket, not abort."""
    root = _root(tmp_path)
    ch = root / "sdd-plus" / "changes" / "half"
    ch.mkdir(parents=True)
    (ch / "brief.md").write_text("# B\n", encoding="utf-8")   # only one of five
    bucket, detail = sdd._classify_packet(ch, root / "sdd-plus" / "specs" / "capabilities")
    assert bucket == "IN-PROGRESS" and "missing" in detail


def test_triage_lists_buckets_and_survives_a_broken_packet(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "good")                                        # ARCHIVE-READY (no deltas)
    (root / "sdd-plus" / "changes" / "broken").mkdir()        # missing everything
    out = _run(root, "triage").stdout
    assert "ARCHIVE-READY" in out and "good" in out
    assert "broken" in out                                    # not skipped / not crashed


def test_triage_empty(tmp_path):
    assert "No active" in _run(_root(tmp_path), "triage").stdout


# ---- _replace_result_section / _unsynced_requirements ----

def test_replace_result_section_swaps_body():
    out = sdd._replace_result_section("# V\n\n## Result\n\nPending.\n", "Abandoned — x")
    assert "Abandoned — x" in out and "Pending." not in out


def test_replace_result_section_appends_when_absent():
    out = sdd._replace_result_section("# V\nno result section\n", "Abandoned — x")
    assert "## Result" in out and "Abandoned — x" in out


def test_unsynced_requirements_lists_absent_ones(tmp_path):
    root = _root(tmp_path)
    ch = _pkt(root, "u",
              delta="Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: Zeta\nSHALL.\n",
              living="# Capability: demo-cap\n\n## Requirements\n")
    missing = sdd._unsynced_requirements(ch, root / "sdd-plus" / "specs" / "capabilities")
    assert missing == ["demo-cap: Zeta"]


# ---- archive --abandon ----

def test_abandon_records_absence_never_a_pass(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "dead", files=dict(COMPLETE, **{"verification.md": "# V\n## Result\nPending.\n"}))
    r = _run(root, "archive", "dead", "--abandon", "--reason", "stale, superseded by X")
    assert r.returncode == 0 and "Abandoned (never verified)" in r.stdout
    arch = list((root / "sdd-plus" / "archive").glob("*-dead"))
    assert arch
    verif = (arch[0] / "verification.md").read_text(encoding="utf-8")
    assert "Abandoned" in verif and "never verified" in verif and "PASS" not in verif
    assert "Override" in (arch[0] / "decision-log.md").read_text(encoding="utf-8")
    assert not (root / "sdd-plus" / "changes" / "dead").exists()   # left changes/, only moved


def test_abandon_warns_when_it_buries_unsynced_spec(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "buries",
         delta="Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: Orphan\nSHALL.\n",
         living="# Capability: demo-cap\n\n## Requirements\n")
    r = _run(root, "archive", "buries", "--abandon", "--reason", "giving up")
    assert r.returncode == 0
    assert "buries spec knowledge" in r.stdout and "demo-cap: Orphan" in r.stdout


def test_abandon_requires_reason(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "x")
    r = _run(root, "archive", "x", "--abandon")
    assert r.returncode != 0 and "--reason" in r.stderr
    assert (root / "sdd-plus" / "changes" / "x").exists()          # nothing moved


def test_abandon_and_force_are_mutually_exclusive(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "x")
    r = _run(root, "archive", "x", "--abandon", "--force", "--reason", "y")
    assert r.returncode != 0 and "not both" in r.stderr


def test_abandon_never_deletes_only_moves(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "keep")
    _run(root, "archive", "keep", "--abandon", "--reason", "z")
    assert list((root / "sdd-plus" / "archive").glob("*-keep"))     # exists in archive


# ---- verifier findings 1-4 ----

def test_abandon_warns_on_non_canonical_and_unattributable_deltas(tmp_path):
    """Finding 1: the entomb warning was silent for grammar the sync gate can't
    verify — exactly the messy-packet case abandon targets. triage/verify are loud
    about it; abandon must not be the one place that goes quiet."""
    root = _root(tmp_path)
    ch = _pkt(root, "murky")
    (ch / "specs" / "nc.md").write_text(                       # non-canonical grammar
        "Capability: demo-cap\n\n## ADDED Requirements\n\n### R7 — Buried\nSHALL.\n",
        encoding="utf-8")
    (ch / "specs" / "noattr.md").write_text(                   # no valid Capability line
        "Capability: <name>\n\n## ADDED Requirements\n\n### Requirement: X\nSHALL.\n",
        encoding="utf-8")
    r = _run(root, "archive", "murky", "--abandon", "--reason", "giving up")
    assert r.returncode == 0
    assert "cannot be verified" in r.stdout                    # the new coverage
    assert "nc.md" in r.stdout and "noattr.md" in r.stdout


def test_abandon_collision_leaves_the_packet_untouched(tmp_path):
    """Finding 2: the collision check now precedes any mutation, so a name clash
    can't leave a half-abandoned packet or append a duplicate Override."""
    import datetime
    root = _root(tmp_path)
    ch = _pkt(root, "clash", files=dict(COMPLETE, **{
        "verification.md": "# V\n## Result\nPending.\n"}))
    (root / "sdd-plus" / "archive").mkdir(parents=True)
    (root / "sdd-plus" / "archive" / f"{datetime.date.today().isoformat()}-clash").mkdir()
    r = _run(root, "archive", "clash", "--abandon", "--reason", "x")
    assert r.returncode != 0                                   # refused
    assert "Pending." in (ch / "verification.md").read_text(encoding="utf-8")  # NOT abandoned
    assert "Override" not in (ch / "decision-log.md").read_text(encoding="utf-8")  # NOT stamped


def test_abandon_scrubs_a_stray_verdict_on_a_malformed_result_heading(tmp_path):
    """Finding 3: a 'PASS' written onto a malformed '## Result: PASS' heading must
    not survive an abandon — the heading is normalized clean."""
    root = _root(tmp_path)
    _pkt(root, "stray", files=dict(COMPLETE, **{
        "verification.md": "# V\n## Result: PASS\n\nall good\n"}))
    r = _run(root, "archive", "stray", "--abandon", "--reason", "actually not")
    assert r.returncode == 0
    verif = list((root / "sdd-plus" / "archive").glob("*-stray"))[0] / "verification.md"
    assert "PASS" not in verif.read_text(encoding="utf-8")     # no stray verdict
    assert "Abandoned" in verif.read_text(encoding="utf-8")


def test_abandon_rejects_whitespace_only_reason(tmp_path):
    root = _root(tmp_path)
    _pkt(root, "ws")
    r = _run(root, "archive", "ws", "--abandon", "--reason", "   ")
    assert r.returncode != 0 and "non-empty --reason" in r.stderr
    assert (root / "sdd-plus" / "changes" / "ws").exists()     # nothing moved
