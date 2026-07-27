from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

import orchestrator


FAKE_CLAUDE = Path(__file__).with_name("fake_claude.py")


def _fake_executable(tmp_path: Path) -> Path:
    if sys.platform == "win32":
        wrapper = tmp_path / "claude.cmd"
        wrapper.write_text(
            f'@"{sys.executable}" "{FAKE_CLAUDE}" %*\r\n',
            encoding="utf-8",
        )
        return wrapper
    wrapper = tmp_path / "claude"
    wrapper.write_text(
        f"#!/bin/sh\nexec {json.dumps(sys.executable)} "
        f"{json.dumps(str(FAKE_CLAUDE))} \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


def _peer(tmp_path: Path, **kwargs: object) -> orchestrator.ClaudePeer:
    return orchestrator.ClaudePeer(
        _fake_executable(tmp_path),
        timeout=int(kwargs.get("timeout", 20)),
        budget_usd=float(kwargs.get("budget_usd", 1.0)),
    )


def _log_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_empty_and_secret_plans_refuse_before_peer_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    controller = orchestrator.NegotiationController(_peer(tmp_path), round_cap=2)
    with pytest.raises(orchestrator.OrchestratorError, match="must not be empty"):
        controller.one_round("  ", 1)
    with pytest.raises(orchestrator.OrchestratorError, match="secret policy"):
        controller.one_round("api_key=abcdefghijklmnop", 1)
    assert not log.exists()


def test_peer_status_distinguishes_absent_and_unauthenticated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absent = orchestrator.ClaudePeer(tmp_path / "missing-claude")
    assert absent.status()["status"] == "absent"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_AUTH", "0")
    assert _peer(tmp_path).status()["status"] == "unauthenticated"


def test_peer_status_does_not_strengthen_authentication_to_operational(
    tmp_path: Path,
) -> None:
    status = _peer(tmp_path).status()
    assert status["status"] == "auth_ready"
    assert status["authentication"] == "ready"
    assert status["operational"] == "not_checked"


def test_peer_call_uses_only_structured_output_tool_and_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    plan = "Implement a bounded, tested adapter."
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round(plan, 1)
    assert result["ok"] is True
    assert result["loop"]["converged"] is True
    assert result["peer"]["status"] == "operational_ready"
    assert result["usage"]["requested_model_observed"] is True
    assert result["usage"]["additional_models_observed"] == []

    calls = _log_lines(log)
    assert len(calls) == 2
    call = calls[-1]
    argv = call["argv"]
    assert argv[argv.index("--model") + 1] == "claude-opus-5"
    assert argv[argv.index("--tools") + 1] == "StructuredOutput"
    assert argv[argv.index("--permission-mode") + 1] == "default"
    assert "--safe-mode" in argv
    assert "--strict-mcp-config" in argv
    assert "--no-chrome" in argv
    assert "--no-session-persistence" in argv
    assert "--max-budget-usd" in argv
    assert "--fallback-model" not in argv
    assert plan not in " ".join(argv)
    assert plan in call["prompt"]
    assert "untrusted DATA" in call["prompt"]
    assert Path(call["cwd"]) != Path.cwd()


def test_peer_schema_stays_within_claude_supported_subset() -> None:
    assert "$schema" not in orchestrator.CRITIQUE_SCHEMA
    assert orchestrator.CRITIQUE_SCHEMA["additionalProperties"] is False


def test_converged_flag_with_blockers_is_not_trusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_CONVERGED", "1")
    monkeypatch.setenv(
        "DRYDOCK_FAKE_CLAUDE_BLOCKERS", '["mechanism does not back claim"]'
    )
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["ok"] is True
    assert result["loop"]["continue"] is True
    assert result["loop"]["converged"] is False


def test_round_cap_returns_unresolved_disagreement_to_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_CONVERGED", "0")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_BLOCKERS", '["still blocked"]')
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=1
    ).one_round("A real plan.", 1)
    assert result["loop"]["continue"] is False
    assert result["loop"]["converged"] is False
    assert "return to Owner" in result["loop"]["reason"]


def test_nonzero_or_is_error_overrides_success_subtype(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SUBTYPE", "success")
    result = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert result["ok"] is False
    assert result["stage"] == "process_failure"
    assert result["subtype"] == "success"


@pytest.mark.parametrize(
    "message",
    [
        "failed to generate structured output",
        "a separate process failed",
        "usage metadata was malformed",
        "quota accounting was unavailable",
    ],
)
def test_generic_keyword_fragments_are_not_rate_limit_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_RESULT", message)
    result = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert result["stage"] == "process_failure"
    assert result["failure_classification"] == "no_explicit_rate_limit_marker"


@pytest.mark.parametrize(
    ("subtype", "message", "basis"),
    [
        ("session_rate_limited", "peer unavailable", "structured_subtype"),
        ("failure", "usage limit reached", "explicit_result_phrase"),
        ("failure", "rate limit exceeded", "explicit_result_phrase"),
        ("failure", "quota exceeded", "explicit_result_phrase"),
    ],
)
def test_explicit_rate_limit_markers_are_classified_without_raw_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subtype: str,
    message: str,
    basis: str,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SUBTYPE", subtype)
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_RESULT", message)
    result = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert result["stage"] == "rate_limited"
    assert result["failure_classification"] == basis
    assert message not in json.dumps(result)


def test_structured_error_type_is_rate_limit_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_ERROR_TYPE", "rate_limit_error")
    result = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert result["stage"] == "rate_limited"
    assert result["failure_classification"] == "structured_error_type"


def test_operational_peer_failure_continues_single_pilot_without_convergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SUBTYPE", "session_rate_limited")
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["ok"] is False
    assert result["workflow"] == {
        "action": "continue_codex_only",
        "mode": "single_pilot",
        "peer_convergence": "not_established",
        "reason": "peer operationally unavailable; Codex governance remains active",
    }


def test_absent_peer_continues_codex_governance_without_peer_claim(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "claude-missing"
    peer = orchestrator.ClaudePeer(
        missing,
        model="claude-opus-5",
        timeout=2,
        budget_usd=0.1,
    )
    result = orchestrator.NegotiationController(
        peer, round_cap=2
    ).one_round("A real plan.", 1)
    assert result["stage"] == "peer_unavailable"
    assert result["peer"]["status"] == "absent"
    assert result["workflow"]["action"] == "continue_codex_only"
    assert result["workflow"]["peer_convergence"] == "not_established"


def test_contract_invalid_peer_result_returns_to_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_MALFORMED", "1")
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["stage"] == "malformed_critique"
    assert result["workflow"]["action"] == "return_to_owner"
    assert result["workflow"]["mode"] == "blocked"
    assert result["workflow"]["peer_convergence"] == "not_established"


def test_malformed_schema_model_mismatch_and_budget_violation_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    peer = _peer(tmp_path, budget_usd=0.1)
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_MALFORMED", "1")
    malformed = peer.critique("A real plan.", round_number=1, round_cap=2)
    assert malformed["stage"] == "malformed_critique"
    assert malformed["wire_shape"]["structured_output"]["type"] == "object"
    assert "result" not in malformed["wire_shape"]["keys"]

    monkeypatch.delenv("DRYDOCK_FAKE_CLAUDE_MALFORMED")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_MODEL", "claude-other")
    mismatch = peer.critique("A real plan.", round_number=1, round_cap=2)
    assert mismatch["stage"] == "model_mismatch"

    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_MODEL", "claude-opus-5")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_COST", "0.2")
    budget = peer.critique("A real plan.", round_number=1, round_cap=2)
    assert budget["stage"] == "budget_violation"


def test_missing_model_or_cost_evidence_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_MODEL_USAGE", "1")
    missing_model = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert missing_model["stage"] == "model_unproven"

    monkeypatch.delenv("DRYDOCK_FAKE_CLAUDE_NO_MODEL_USAGE")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_COST", "1")
    missing_cost = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert missing_cost["stage"] == "cost_unproven"


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_peer_cost_and_budget_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_COST", value)
    result = _peer(tmp_path).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    assert result["ok"] is False
    assert result["stage"] == "malformed_envelope"
    with pytest.raises(orchestrator.OrchestratorError, match="positive"):
        orchestrator.ClaudePeer(
            _fake_executable(tmp_path),
            budget_usd=float(value),
        )


def test_timeout_is_unavailable_not_convergence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SLEEP", "3")
    result = orchestrator.NegotiationController(
        _peer(tmp_path, timeout=1), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["ok"] is False
    assert result["stage"] == "timeout"
    assert result["workflow"]["action"] == "continue_codex_only"
    assert result["workflow"]["peer_convergence"] == "not_established"


def test_timeout_terminates_delayed_descendant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = tmp_path / "escaped-descendant.txt"
    monkeypatch.setenv(
        "DRYDOCK_FAKE_CLAUDE_DESCENDANT_SENTINEL", str(sentinel)
    )
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_DESCENDANT_DELAY", "2.5")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SLEEP", "5")
    started = time.monotonic()
    result = _peer(tmp_path, timeout=1).critique(
        "A real plan.", round_number=1, round_cap=2
    )
    elapsed = time.monotonic() - started
    assert result["stage"] == "timeout"
    assert result["cleanup"]["direct_process_absent"] is True
    assert result["cleanup"]["boundary"] == (
        "windows_job_object"
        if sys.platform == "win32"
        else "posix_process_group_best_effort"
    )
    assert elapsed < 10
    time.sleep(3)
    assert not sentinel.exists()


def test_pace_forecast_reports_unavailable_and_at_risk() -> None:
    unavailable = orchestrator.pace_forecast(
        target_hours=3,
        remaining_percent=None,
        reset_seconds=7200,
        measured_burn_percent_per_hour=10,
    )
    assert unavailable["status"] == "unavailable"
    at_risk = orchestrator.pace_forecast(
        target_hours=3,
        remaining_percent=10,
        reset_seconds=7200,
        measured_burn_percent_per_hour=10,
    )
    assert at_risk["status"] == "at_risk"
    assert at_risk["recommendation"]


def test_structured_output_string_and_nested_envelopes_are_normalized() -> None:
    critique = {
        "converged": True,
        "overall": "coherent",
        "blocking_concerns": [],
        "gaps": [],
        "risks": [],
        "task_decomposition": [],
    }
    as_string = {"structured_output": json.dumps(critique)}
    nested = {"result": json.dumps({"structured_output": critique})}
    assert orchestrator.extract_structured_critique(as_string) == critique
    assert orchestrator.extract_structured_critique(nested) == critique


def test_strict_json_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate JSON key"):
        orchestrator._strict_json_loads(
            '{"converged":true,"converged":false}'
        )


def test_wire_shape_diagnostics_never_include_result_content() -> None:
    shape = orchestrator.envelope_shape(
        {
            "type": "result",
            "structured_output": None,
            "result": '{"private":"do not report"}',
        }
    )
    assert shape["structured_output"] == {"presence": "null"}
    assert shape["result"] == {
        "presence": "present",
        "type": "string",
        "length": 27,
        "looks_like_json": True,
    }
    assert "private" not in json.dumps(shape)
