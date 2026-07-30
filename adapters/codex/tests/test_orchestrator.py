from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

import orchestrator
import orchestration_control as control
import orchestration_evidence as evidence


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
        review_input_bytes=int(
            kwargs.get(
                "review_input_bytes",
                orchestrator.DEFAULT_REVIEW_INPUT_BYTES,
            )
        ),
        review_kind=str(
            kwargs.get("review_kind", orchestrator.DEFAULT_REVIEW_KIND)
        ),
        effort=str(kwargs.get("effort", orchestrator.DEFAULT_PEER_EFFORT)),
        invocation_store=kwargs.get("invocation_store"),
        run_ledger=kwargs.get("run_ledger"),
        candidate_fingerprint=kwargs.get("candidate_fingerprint"),
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


def test_phase_input_budget_refuses_before_any_peer_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    result = _peer(tmp_path, review_input_bytes=64).critique(
        "A bounded but non-empty plan.",
        round_number=1,
        round_cap=2,
    )
    assert result["stage"] == "input_budget_exceeded"
    assert result["provider_spawned"] is False
    assert result["routes"] == [
        "repository_aware_owner_relay",
        "separately_approved_digest_bound_snapshot",
        "smaller_review_with_omissions_disclosed",
    ]
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
    assert argv[argv.index("--effort") + 1] == "high"
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
    assert "Critique only technical correctness" in call["prompt"]
    assert "does not interpret or widen Owner authority" not in call["prompt"]
    assert "Do not create or widen those permissions" in call["prompt"]
    assert Path(call["cwd"]) != Path.cwd()
    assert result["review_configuration"] == {
        "effort": "high",
        "kind": "plan",
        "ledger_phase": "plan_peer",
        "structured_output_bounded": True,
    }


def test_implementation_review_uses_requested_effort_and_compact_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    result = _peer(
        tmp_path,
        review_kind="implementation",
        effort="medium",
    ).critique(
        "Review the exact candidate diff and focused proof.",
        round_number=1,
        round_cap=1,
    )
    assert result["ok"] is True
    assert result["review_configuration"] == {
        "effort": "medium",
        "kind": "implementation",
        "ledger_phase": "cross_review",
        "structured_output_bounded": True,
    }
    call = [item for item in _log_lines(log) if item["prompt"]][-1]
    argv = call["argv"]
    assert argv[argv.index("--effort") + 1] == "medium"
    assert "Review kind: implementation." in call["prompt"]
    assert "keep task_decomposition empty" in call["prompt"]
    assert "smallest remediation tasks" in call["prompt"]


@pytest.mark.parametrize(
    ("argument", "value", "message"),
    [
        ("review_kind", "security", "review kind"),
        ("effort", "unbounded", "effort"),
    ],
)
def test_invalid_review_controls_refuse_before_peer_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argument: str,
    value: str,
    message: str,
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    with pytest.raises(orchestrator.OrchestratorError, match=message):
        _peer(tmp_path, **{argument: value})
    assert not log.exists()


def test_official_peer_wrapper_consumes_admission_before_provider_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    plan_body = b"# exact peer plan\n"
    (repo / "plan.md").write_bytes(plan_body)
    state = evidence.state_root(tmp_path / "workflow-state")
    objective_id = "34" * 16
    objective_digest = hashlib.sha256(b"peer objective").hexdigest()
    task_id = "peer-task"
    owner_action = hashlib.sha256(b"peer owner action").hexdigest()
    now = time.time()
    authority = {
        "allowed_actions": ["peer"],
        "allowed_paths": ["plan.md"],
        "circuit_limits": {
            "elapsed_seconds": 900,
            "input_bytes": 65_536,
            "phase_entries": 8,
            "procedural_failures": 2,
            "provider_usd": 3.0,
        },
        "expires_at": now + 600,
        "issued_at": now - 10,
        "limits": {
            "elapsed_seconds": 900,
            "input_bytes": 65_536,
            "peer_rounds": 2,
            "provider_usd": 3.0,
        },
        "objective_digest": objective_digest,
        "objective_id": objective_id,
        "owner_action_digest": owner_action,
        "predecessor_objective_id": None,
        "push": None,
        "repository_root": str(repo.resolve(strict=True)),
        "schema_version": control.SCHEMA_VERSION,
        "task_id": task_id,
    }
    plan = {
        "mode": "FULL",
        "objective_digest": objective_digest,
        "objective_id": objective_id,
        "phases": ["preflight", "plan_peer", "complete"],
        "primary_skill": "drydock-orchestrate",
        "push": None,
        "required_actions": ["peer"],
        "required_paths": ["plan.md"],
        "resource_request": {
            "elapsed_seconds": 600,
            "input_bytes": 32_768,
            "peer_rounds": 2,
            "provider_usd": 1.0,
        },
        "revision": 1,
        "schema_version": control.SCHEMA_VERSION,
        "source_plan_path": "plan.md",
        "source_plan_sha256": hashlib.sha256(plan_body).hexdigest(),
        "summary": "Prove peer admission is consumed before provider spawn.",
        "supersedes": None,
    }
    store = control.WorkflowStore(state, objective_id)
    store.start(authority, plan, expected_task_id=task_id, now=now)
    review = tmp_path / "review.md"
    review.write_text("A bounded peer review.", encoding="utf-8")
    review_bytes = review.read_bytes()
    review_digest = hashlib.sha256(review_bytes).hexdigest()
    admission = store.admit(
        "plan_peer",
        input_digest=review_digest,
        input_bytes=len(review_bytes),
        now=now + 1,
    )
    ledger = evidence.RunLedger.start(
        state,
        objective_digest=objective_digest,
        owner_action_digest=owner_action,
    )
    log = tmp_path / "peer-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    original_peer = orchestrator.ClaudePeer

    def fake_peer_factory(*args: object, **kwargs: object) -> object:
        return original_peer(
            _fake_executable(tmp_path),
            model=str(kwargs["model"]),
            timeout=int(kwargs["timeout"]),
            budget_usd=float(kwargs["budget_usd"]),
            review_input_bytes=int(kwargs["review_input_bytes"]),
            review_kind=str(kwargs["review_kind"]),
            effort=str(kwargs["effort"]),
            invocation_store=kwargs["invocation_store"],
            run_ledger=kwargs["run_ledger"],
            candidate_fingerprint=str(kwargs["candidate_fingerprint"]),
        )

    monkeypatch.setattr(orchestrator, "ClaudePeer", fake_peer_factory)
    monkeypatch.chdir(repo)
    argv = [
        "critique",
        "--file",
        str(review),
        "--round",
        "1",
        "--cap",
        "2",
        "--run-id",
        ledger.run_id,
        "--candidate-fingerprint",
        "c" * 64,
        "--state-dir",
        str(state),
        "--workflow-objective-id",
        objective_id,
        "--workflow-admission-id",
        str(admission["admission_id"]),
        "--workflow-phase",
        "plan_peer",
        "--workflow-input-digest",
        review_digest,
    ]
    assert orchestrator.main(argv) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["ok"] is True
    assert store.read()["admission"]["state"] == "consumed"
    first_calls = len(_log_lines(log))

    assert orchestrator.main(argv) == 1
    second = json.loads(capsys.readouterr().out)
    assert second["stage"] == "input_error"
    assert "consumed" in second["error"]
    assert len(_log_lines(log)) == first_calls


def test_durable_peer_result_is_recovered_without_second_model_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    root = evidence.state_root(tmp_path / "state")
    ledger = evidence.RunLedger.start(
        root,
        objective_digest="a" * 64,
        owner_action_digest="b" * 64,
    )
    store = evidence.InvocationStore(root)
    peer = _peer(
        tmp_path,
        invocation_store=store,
        run_ledger=ledger,
        candidate_fingerprint="c" * 64,
    )
    first = peer.critique("A real plan.", round_number=1, round_cap=2)
    assert first["ok"] is True
    assert first["invocation"]["status"] == "persisted"
    second = peer.critique("A real plan.", round_number=1, round_cap=2)
    assert second["ok"] is True
    assert second["recovery"]["recovered"] is True
    calls = _log_lines(log)
    assert len([call for call in calls if call["prompt"]]) == 1
    assert ledger.read()["usage"]["calls"] == 1


@pytest.mark.parametrize(
    ("first_controls", "second_controls"),
    [
        (
            {"review_kind": "plan", "effort": "high"},
            {"review_kind": "plan", "effort": "medium"},
        ),
        (
            {"review_kind": "plan", "effort": "high"},
            {"review_kind": "implementation", "effort": "high"},
        ),
    ],
)
def test_review_kind_and_effort_are_bound_to_invocation_identity(
    tmp_path: Path,
    first_controls: dict[str, str],
    second_controls: dict[str, str],
) -> None:
    root = evidence.state_root(tmp_path / "state")
    ledger = evidence.RunLedger.start(
        root,
        objective_digest="a" * 64,
        owner_action_digest="b" * 64,
    )
    store = evidence.InvocationStore(root)
    common = {
        "invocation_store": store,
        "run_ledger": ledger,
        "candidate_fingerprint": "c" * 64,
    }
    first = _peer(
        tmp_path,
        **common,
        **first_controls,
    ).critique("An exact review input.", round_number=1, round_cap=1)
    second = _peer(
        tmp_path,
        **common,
        **second_controls,
    ).critique("An exact review input.", round_number=1, round_cap=1)
    assert first["ok"] is True
    assert second["ok"] is True
    assert (
        first["invocation"]["fingerprint"]
        != second["invocation"]["fingerprint"]
    )


def test_phase_envelope_exhaustion_stops_before_second_model_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "claude-log.jsonl"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_LOG", str(log))
    root = evidence.state_root(tmp_path / "state")
    phase_limit = evidence.Envelope(60, 1, 20000, 2)
    ledger = evidence.RunLedger.start(
        root,
        objective_digest="a" * 64,
        owner_action_digest="b" * 64,
        phase_envelopes={"plan_peer": phase_limit},
    )
    peer = _peer(
        tmp_path,
        invocation_store=evidence.InvocationStore(root),
        run_ledger=ledger,
        candidate_fingerprint="c" * 64,
    )
    first = peer.critique("First plan.", round_number=1, round_cap=2)
    assert first["ok"] is True
    second = orchestrator.NegotiationController(peer).one_round(
        "Different plan.", 1
    )
    assert second["stage"] == "envelope_exhausted"
    assert second["workflow"]["action"] == "return_to_owner"
    assert len([call for call in _log_lines(log) if call["prompt"]]) == 1


def test_peer_schema_stays_within_claude_supported_subset() -> None:
    assert "$schema" not in orchestrator.CRITIQUE_SCHEMA
    assert orchestrator.CRITIQUE_SCHEMA["additionalProperties"] is False
    properties = orchestrator.CRITIQUE_SCHEMA["properties"]
    assert (
        properties["overall"]["maxLength"]
        == orchestrator.MAX_REVIEW_OVERALL_CHARS
    )
    for name in (
        "blocking_concerns",
        "gaps",
        "required_context",
        "risks",
        "task_decomposition",
    ):
        assert properties[name]["maxItems"] == orchestrator.MAX_REVIEW_ITEMS
    assert (
        properties["task_decomposition"]["items"]["properties"]["task"][
            "maxLength"
        ]
        == orchestrator.MAX_REVIEW_TASK_CHARS
    )


def test_maximum_structured_review_leaves_terminal_record_headroom() -> None:
    item = "i" * orchestrator.MAX_REVIEW_ITEM_CHARS
    task = {
        "model_tier": "workhorse",
        "owner": "codex",
        "rationale": item,
        "task": "t" * orchestrator.MAX_REVIEW_TASK_CHARS,
    }
    critique: dict[str, object] = {
        "blocking_concerns": [item] * orchestrator.MAX_REVIEW_ITEMS,
        "converged": False,
        "context_status": "insufficient_context",
        "gaps": [item] * orchestrator.MAX_REVIEW_ITEMS,
        "overall": "o" * orchestrator.MAX_REVIEW_OVERALL_CHARS,
        "required_context": [item] * orchestrator.MAX_REVIEW_ITEMS,
        "review_input_sha256": "a" * 64,
        "risks": [item] * orchestrator.MAX_REVIEW_ITEMS,
        "task_decomposition": [task] * orchestrator.MAX_REVIEW_ITEMS,
    }
    assert orchestrator.validate_critique(critique) == critique
    encoded = json.dumps(
        critique, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    assert len(encoded) < evidence.MAX_TERMINAL_BYTES // 2


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "overall",
            "x" * (orchestrator.MAX_REVIEW_OVERALL_CHARS + 1),
            "overall assessment",
        ),
        (
            "blocking_concerns",
            ["x"] * (orchestrator.MAX_REVIEW_ITEMS + 1),
            "blocking_concerns",
        ),
        (
            "task_decomposition",
            [
                {
                    "model_tier": "workhorse",
                    "owner": "codex",
                    "rationale": "bounded",
                    "task": "x"
                    * (orchestrator.MAX_REVIEW_TASK_CHARS + 1),
                }
            ],
            "task decomposition",
        ),
    ],
)
def test_peer_validation_enforces_structured_output_bounds(
    field: str, value: object, message: str
) -> None:
    critique: dict[str, object] = {
        "blocking_concerns": [],
        "converged": True,
        "context_status": "sufficient",
        "gaps": [],
        "overall": "bounded",
        "required_context": [],
        "review_input_sha256": "a" * 64,
        "risks": [],
        "task_decomposition": [],
    }
    critique[field] = value
    with pytest.raises(orchestrator.OrchestratorError, match=message):
        orchestrator.validate_critique(critique)


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


def test_insufficient_context_is_nonconverging_technical_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "DRYDOCK_FAKE_CLAUDE_CONTEXT_STATUS", "insufficient_context"
    )
    monkeypatch.setenv(
        "DRYDOCK_FAKE_CLAUDE_REQUIRED_CONTEXT",
        '["exact transition table digest"]',
    )
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_CONVERGED", "0")
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A bounded delta.", 1)
    assert result["ok"] is True
    assert result["critique"]["context_status"] == "insufficient_context"
    assert result["loop"]["converged"] is False
    assert result["loop"]["continue"] is True
    assert "technical outcome" in result["loop"]["reason"]


def test_peer_review_input_identity_mismatch_cannot_converge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "DRYDOCK_FAKE_CLAUDE_REVIEW_INPUT_SHA256", "f" * 64
    )
    result = _peer(tmp_path).critique(
        "A bounded delta.", round_number=1, round_cap=2
    )
    assert result["ok"] is False
    assert result["stage"] == "review_input_identity_mismatch"


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
    assert result["failure_classification"] == "structured_subtype_not_allowlisted"


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


def test_budget_control_failure_returns_to_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SUBTYPE", "error_max_budget_usd")
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["stage"] == "budget_violation"
    assert result["workflow"]["action"] == "return_to_owner"
    assert result["workflow"]["peer_convergence"] == "not_established"


def test_unknown_structured_subtype_returns_to_owner_without_raw_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_result = "private provider failure detail"
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_IS_ERROR", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_SUBTYPE", "invented_provider_abort")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_RESULT", raw_result)
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["stage"] == "unmapped_control_failure"
    assert result["workflow"]["action"] == "return_to_owner"
    assert raw_result not in json.dumps(result)


def test_bare_zero_cost_nonzero_exit_continues_single_pilot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_SUBTYPE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_STRUCTURED_OUTPUT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_COST", "0")
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["stage"] == "process_failure"
    assert result["failure_classification"] == "ordinary_nonzero_zero_cost"
    assert result["workflow"] == {
        "action": "continue_codex_only",
        "mode": "single_pilot",
        "peer_convergence": "not_established",
        "reason": "peer operationally unavailable; Codex governance remains active",
    }


@pytest.mark.parametrize(
    ("missing_cost", "cost"),
    [(True, None), (False, "0.01")],
)
def test_bare_nonzero_exit_without_proven_zero_cost_returns_to_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing_cost: bool,
    cost: str | None,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_EXIT", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_SUBTYPE", "1")
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_STRUCTURED_OUTPUT", "1")
    if missing_cost:
        monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_NO_COST", "1")
    else:
        assert cost is not None
        monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_COST", cost)
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["workflow"]["action"] == "return_to_owner"
    assert result["workflow"]["peer_convergence"] == "not_established"


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


def test_high_impact_objective_discloses_skipped_critique(
    tmp_path: Path,
) -> None:
    peer = orchestrator.ClaudePeer(tmp_path / "missing-claude")
    result = orchestrator.NegotiationController(
        peer,
        objective_properties=["process_boundaries"],
    ).one_round("A real plan.", 1)
    disclosure = result["pre_mutation_critique"]
    assert disclosure["critique_skipped"] is True
    assert disclosure["peer_convergence"] == "not_established"
    assert disclosure["gate_satisfied"] is False
    assert disclosure["trigger"]["mode"] == "FULL"


def test_return_to_owner_has_uniform_pre_mutation_critique_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_MALFORMED", "1")
    result = orchestrator.NegotiationController(
        _peer(tmp_path),
        objective_properties=["permissions"],
    ).one_round("A real plan.", 1)
    assert result["workflow"]["action"] == "return_to_owner"
    assert result["pre_mutation_critique"]["gate_satisfied"] is False
    assert result["pre_mutation_critique"]["trigger"]["critique_required"] is True


def test_unauthenticated_peer_continues_without_claiming_agreement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DRYDOCK_FAKE_CLAUDE_AUTH", "0")
    result = orchestrator.NegotiationController(
        _peer(tmp_path), round_cap=2
    ).one_round("A real plan.", 1)
    assert result["stage"] == "peer_unavailable"
    assert result["peer"]["status"] == "unauthenticated"
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


def test_close_run_cli_reaches_terminal_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    state = tmp_path / "state"
    root = evidence.state_root(state, repository_root=repo)
    ledger = evidence.RunLedger.start(
        root,
        objective_digest="a" * 64,
        owner_action_digest="b" * 64,
    )
    exit_code = orchestrator.main(
        [
            "close-run",
            "--run-id",
            ledger.run_id,
            "--status",
            "cancelled_by_owner",
            "--owner-action-digest",
            "c" * 64,
            "--state-dir",
            str(state),
        ]
    )
    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "cancelled_by_owner"
    assert ledger.read()["status"] == "cancelled_by_owner"


def test_official_proof_refuses_intermediate_scope_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state = tmp_path / "state"
    candidate = "c" * 64
    commit = "d" * 40
    monkeypatch.setattr(
        orchestrator,
        "repository_fingerprints",
        lambda *args, **kwargs: {
            "reuse_eligible": True,
            "head": commit,
            "executable_surface_sha256": candidate,
        },
    )

    def must_not_execute(*args: object, **kwargs: object) -> object:
        pytest.fail("intermediate official proof reached process execution")

    monkeypatch.setattr(orchestrator, "run_proof_command", must_not_execute)

    exit_code = orchestrator.main(
        [
            "proof-run",
            "--repo",
            str(repo),
            "--commit",
            commit,
            "--scope",
            "intermediate",
            "--packet-root",
            "sdd-plus/changes/test",
            "--state-dir",
            str(state),
            "--workflow-objective-id",
            "01" * 16,
            "--workflow-admission-id",
            "02" * 16,
            "--workflow-input-digest",
            "a" * 64,
            "--workflow-candidate-digest",
            candidate,
            "--",
            sys.executable,
            "-m",
            "pytest",
            "-q",
        ]
    )

    assert exit_code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["stage"] == "input_error"
    assert "scope=full_required_suite" in result["error"]


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
