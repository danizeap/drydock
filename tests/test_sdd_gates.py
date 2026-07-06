"""Behavioral tests for the deterministic packet gates (change-packet-gates spec)."""
import pytest

import sdd


# --- placeholder gate ------------------------------------------------------
def test_placeholder_detects_whole_line():
    assert sdd.text_has_placeholder("TBD")
    assert sdd.text_has_placeholder("- TBD")


def test_placeholder_detects_checkbox():
    assert sdd.text_has_placeholder("- [ ] TBD")


def test_placeholder_detects_table_cell():
    assert sdd.text_has_placeholder("| 2026-07-06 | TBD | TBD | TBD |")


def test_placeholder_detects_change_name_token():
    assert sdd.text_has_placeholder("Change: {{CHANGE_NAME}}")


def test_placeholder_ignores_prose_mentioning_tbd():
    assert not sdd.text_has_placeholder("Nothing is TBD anymore; the shape is decided.")


def test_placeholder_ignores_inline_mention_of_forms():
    # a brief/decision-log describing the bug quotes the forms in backticks
    assert not sdd.text_has_placeholder("The shipped templates use `- [ ] TBD` and `| TBD |` cells.")


def test_placeholder_detects_real_table_row():
    assert sdd.text_has_placeholder("| 2026-07-06 | TBD | TBD | TBD |")


def test_placeholder_ignores_table_row_quoting_the_form():
    # a decision-log row that quotes `| TBD |` as an example is not residue
    assert not sdd.text_has_placeholder("| 2026 | catch `| TBD |` cells | Flag any TBD substring (rejected) |")


def test_placeholder_ignores_change_name_in_backticks():
    assert not sdd.text_has_placeholder("The gate flags an unreplaced `{{CHANGE_NAME}}` token.")


def test_placeholder_ignores_code_fence():
    txt = "```\n- [ ] TBD\n```\nAll real content, decided.\n"
    assert not sdd.text_has_placeholder(txt)


def test_verification_result_pending_detected():
    assert sdd.verification_result_is_pending("## Result\n\nPending.\n")


def test_verification_result_filled_ok():
    assert not sdd.verification_result_is_pending("## Result\n\nAll checks pass. PASS.\n")


# --- sync-gate matching ----------------------------------------------------
def test_requirement_present_exact(tmp_path):
    living = tmp_path / "cap.md"
    living.write_text("## Requirements\n\n### Requirement: Session Expiry\n", encoding="utf-8")
    assert sdd.requirement_present(living, "Session Expiry")


def test_requirement_present_rejects_substring(tmp_path):
    living = tmp_path / "cap.md"
    living.write_text("## Requirements\n\n### Requirement: Session Expiry\n", encoding="utf-8")
    assert not sdd.requirement_present(living, "Session")


def test_added_requirements_stop_at_next_section(tmp_path):
    f = tmp_path / "d.md"
    f.write_text(
        "Capability: x\n\n## ADDED Requirements\n\n### Requirement: A\nThe system SHALL a.\n\n"
        "## Notes\n\n### Requirement: B\n",
        encoding="utf-8",
    )
    assert sdd.delta_added_requirements(f) == ["A"]


# --- capability extraction fail-closed -------------------------------------
def test_capability_ignores_code_fence(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("```\nCapability: fake\n```\n\nCapability: real-cap\n", encoding="utf-8")
    assert sdd.delta_capabilities_in_file(f) == ["real-cap"]


def test_capability_rejects_placeholder(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("Capability: <kebab-capability-name, e.g. user-auth, lead-import>\n", encoding="utf-8")
    assert sdd.delta_capabilities_in_file(f) == []


def test_capability_rejects_non_kebab(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("Capability: Not A Kebab Name\n", encoding="utf-8")
    assert sdd.delta_capabilities_in_file(f) == []


def test_capability_accepts_valid_kebab(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("Capability: git-safety-hook\n", encoding="utf-8")
    assert sdd.delta_capabilities_in_file(f) == ["git-safety-hook"]


# --- governed --force ------------------------------------------------------
def test_force_without_reason_is_refused_before_touching_files():
    # the reason check is first in cmd_archive, so it exits before any file access
    with pytest.raises(SystemExit) as exc:
        sdd.cmd_archive("some-change", force=True, reason="")
    assert "--reason" in str(exc.value)


def test_record_override_appends_auditable_entry(tmp_path):
    log = tmp_path / "decision-log.md"
    log.write_text("# Decision Log\n\n## Decisions\n", encoding="utf-8")
    sdd.record_override(tmp_path, ["pending tasks", "unsynced capabilities (x)"], "hotfix per #123")
    text = log.read_text(encoding="utf-8")
    assert "## Override" in text
    assert "pending tasks; unsynced capabilities (x)" in text
    assert "hotfix per #123" in text
    # append-only: the original content is preserved
    assert "## Decisions" in text


def test_record_override_is_append_only(tmp_path):
    log = tmp_path / "decision-log.md"
    log.write_text("# Decision Log\n", encoding="utf-8")
    sdd.record_override(tmp_path, ["a"], "first")
    sdd.record_override(tmp_path, ["b"], "second")
    text = log.read_text(encoding="utf-8")
    assert text.count("## Override") == 2
    assert "first" in text and "second" in text
