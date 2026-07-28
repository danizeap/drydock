from __future__ import annotations

import copy

import pytest

from adapters.codex.drydock.scripts import delegation_contracts as contracts


NOW = "2026-07-28T12:00:00.000Z"
DIGEST_A = "sha256:" + "a" * 64


def envelope(
    objective: str = "Implement the bounded adapter.",
    **overrides: object,
) -> contracts.DelegationEnvelope:
    values = {
        "delegation_id": "delegation-1",
        "run_id": "run-1",
        "task_id": "task-1",
        "task_class": "backend-contract",
        "role": "implementer",
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "permission_profile": "workspace-write",
        "attempt": 1,
        "max_attempts": 2,
        "objective": objective,
        "input_digests": (DIGEST_A,),
        "capacity_snapshot_digest": None,
        "policy_revision": "policy-2",
        "created_at": NOW,
    }
    values.update(overrides)
    return contracts.DelegationEnvelope.create(**values)  # type: ignore[arg-type]


def result(**overrides: object) -> contracts.DelegationResult:
    values = {
        "delegation_id": "delegation-1",
        "run_id": "run-1",
        "runtime_status": "completed",
        "duration_ms": 1200,
        "usage_basis": "provider_reported",
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "output_tokens": 40,
        "reasoning_tokens": 10,
        "reasoning_token_semantics": "included_in_output",
        "total_tokens": 140,
        "cost_basis": "provider_reported",
        "cost_microusd": 1234,
        "artifact_refs": ("changes/run-1.patch",),
        "evidence_refs": ("verification/run-1.json",),
        "error_code": None,
        "untrusted_claimed_terminal_status": "done",
        "untrusted_error_summary": None,
        "completed_at": NOW,
    }
    values.update(overrides)
    return contracts.DelegationResult(**values)  # type: ignore[arg-type]


def observation(
    selected_envelope: contracts.DelegationEnvelope,
    selected_result: contracts.DelegationResult,
    **overrides: object,
) -> contracts.OutcomeObservation:
    values = {
        "observation_id": "observation-1",
        "delegation_id": selected_envelope.delegation_id,
        "run_id": selected_envelope.run_id,
        "envelope_digest": contracts.contract_digest(selected_envelope),
        "result_digest": contracts.contract_digest(selected_result),
        "observer_kind": "verifier",
        "outcome": "accepted",
        "verification": "pass",
        "peer_findings_count": 1,
        "blocking_findings_count": 0,
        "regression_count": 0,
        "evidence_refs": ("verification/observation-1.json",),
        "observed_at": NOW,
    }
    values.update(overrides)
    return contracts.OutcomeObservation(**values)  # type: ignore[arg-type]


def test_schema_v2_request_binding_is_content_stable_not_idempotency() -> None:
    first = envelope("A private runtime objective.")
    second = envelope("A private runtime objective.")
    persisted = first.to_dict()

    assert persisted["schema_version"] == 2
    assert "objective" not in persisted
    assert "idempotency_key" not in persisted
    assert persisted["objective_digest"] == contracts.digest_text(
        "A private runtime objective."
    )
    assert first.request_binding_digest == second.request_binding_digest
    assert "private runtime objective" not in contracts.canonical_json(persisted)

    changed = envelope(permission_profile="read-only")
    assert changed.request_binding_digest != first.request_binding_digest
    tampered = first.to_dict()
    tampered["permission_profile"] = "read-only"
    with pytest.raises(contracts.ContractError, match="request_binding_digest"):
        contracts.DelegationEnvelope.from_dict(tampered)


@pytest.mark.parametrize(
    "factory,value",
    [
        (
            contracts.DelegationEnvelope.from_dict,
            lambda: envelope().to_dict(),
        ),
        (
            contracts.DelegationResult.from_dict,
            lambda: result().to_dict(),
        ),
        (
            contracts.OutcomeObservation.from_dict,
            lambda: observation(envelope(), result()).to_dict(),
        ),
        (
            contracts.CapabilityProfile.from_dict,
            lambda: contracts.CapabilityProfile(
                provider="openai",
                model="gpt-5.6-sol",
                role="implementer",
                task_class="backend-contract",
            ).to_dict(),
        ),
    ],
)
def test_schema_v1_is_explicitly_refused(factory, value) -> None:
    persisted = value()
    persisted["schema_version"] = 1
    with pytest.raises(contracts.ContractError, match="v2 required"):
        factory(persisted)


def test_strict_json_depth_boundary_limit_minus_one_limit_plus_one() -> None:
    def nested(depth: int) -> str:
        return "[" * depth + "0" + "]" * depth

    assert contracts.strict_json_loads(
        nested(contracts.MAX_JSON_DEPTH - 1)
    ) is not None
    assert contracts.strict_json_loads(
        nested(contracts.MAX_JSON_DEPTH)
    ) is not None
    with pytest.raises(contracts.ContractError, match="depth bound"):
        contracts.strict_json_loads(nested(contracts.MAX_JSON_DEPTH + 1))
    with pytest.raises(contracts.ContractError, match="nesting|depth"):
        contracts.strict_json_loads(nested(2000))


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_strict_json_rejects_every_nonfinite_spelling_and_overflow(
    token: str,
) -> None:
    with pytest.raises(contracts.ContractError, match="non-finite"):
        contracts.strict_json_loads('{"number":' + token + "}")


def test_strict_json_rejects_duplicates_and_bounds_integer_digits() -> None:
    with pytest.raises(contracts.ContractError, match="duplicate JSON key"):
        contracts.strict_json_loads('{"status":"ok","status":"failed"}')
    assert contracts.strict_json_loads(
        str(contracts.MAX_INTEGER)
    ) == contracts.MAX_INTEGER
    with pytest.raises(contracts.ContractError, match="magnitude"):
        contracts.strict_json_loads(str(contracts.MAX_INTEGER + 1))
    with pytest.raises(contracts.ContractError, match="digit"):
        contracts.strict_json_loads("1" * (contracts.MAX_JSON_INTEGER_DIGITS + 1))


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-01T00:00:00.000Z",
        "2026-12-31T23:59:59.999Z",
        "2024-02-29T12:34:56.001Z",
    ],
)
def test_exact_utc_millisecond_timestamp_valid_boundaries(timestamp: str) -> None:
    assert contracts.validate_timestamp(timestamp, "timestamp") == timestamp


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-01T00:00:00Z",
        "2026-01-01T00:00:00.00Z",
        "2026-01-01T00:00:00.0000Z",
        "2026-01-01 00:00:00.000Z",
        "2026-01-01T00:00:00.000+00:00",
        "2026-02-29T00:00:00.000Z",
        "2026-01-01T24:00:00.000Z",
        "2026-01-01T23:59:60.000Z",
    ],
)
def test_exact_utc_millisecond_timestamp_invalid_boundaries(
    timestamp: str,
) -> None:
    with pytest.raises(contracts.ContractError, match="match|real UTC"):
        contracts.validate_timestamp(timestamp, "timestamp")


def test_contract_round_trips_and_detaches_nested_untrusted_error() -> None:
    nested = {
        "kind": "model_claim",
        "details": [{"code": "bounded", "retryable": False}],
    }
    original = result(
        runtime_status="failed",
        error_code="provider_failure",
        untrusted_error_summary=nested,
    )
    before = copy.deepcopy(original.to_dict())
    nested["details"][0]["code"] = "mutated"  # type: ignore[index]
    nested["details"].append({"code": "outside"})  # type: ignore[union-attr]

    assert original.to_dict() == before
    assert contracts.DelegationResult.from_dict(before) == original
    assert not isinstance(original.untrusted_error_summary, (dict, list))
    persisted_summary = original.to_dict()["untrusted_error_summary"]
    assert persisted_summary == {
        "kind": "model_claim",
        "details": [{"code": "bounded", "retryable": False}],
    }
    persisted_summary["details"][0]["code"] = "changed copy"  # type: ignore[index]
    assert original.to_dict() == before


def test_runtime_status_and_untrusted_claims_remain_separate() -> None:
    failed = result(
        runtime_status="failed",
        error_code="provider_failure",
        untrusted_claimed_terminal_status="completed",
        untrusted_error_summary={"message": "model says success"},
    )
    persisted = failed.to_dict()
    assert persisted["runtime_status"] == "failed"
    assert persisted["untrusted_claimed_terminal_status"] == "completed"
    assert persisted["untrusted_error_summary"] == {
        "message": "model says success"
    }


def test_usage_basis_reasoning_and_cost_semantics_are_explicit() -> None:
    excluded = result(
        reasoning_token_semantics="excluded_from_output",
        reasoning_tokens=10,
        total_tokens=150,
    )
    assert excluded.to_dict()["usage"]["basis"] == "provider_reported"  # type: ignore[index]
    assert excluded.to_dict()["cost"]["basis"] == "provider_reported"  # type: ignore[index]

    with pytest.raises(contracts.ContractError, match="reasoning semantics"):
        result(
            reasoning_token_semantics="excluded_from_output",
            reasoning_tokens=10,
            total_tokens=140,
        )
    with pytest.raises(contracts.ContractError, match="unavailable usage"):
        result(usage_basis="unavailable")
    unavailable = result(
        usage_basis="unavailable",
        input_tokens=None,
        cached_input_tokens=None,
        output_tokens=None,
        reasoning_tokens=None,
        reasoning_token_semantics="unavailable",
        total_tokens=None,
        cost_basis="unavailable",
        cost_microusd=None,
    )
    assert unavailable.total_tokens is None
    assert unavailable.cost_microusd is None


def test_observation_explicitly_binds_run_envelope_and_result() -> None:
    selected_envelope = envelope()
    selected_result = result()
    selected_observation = observation(selected_envelope, selected_result)
    assert selected_observation.run_id == selected_envelope.run_id
    assert selected_observation.envelope_digest == contracts.contract_digest(
        selected_envelope
    )
    assert selected_observation.result_digest == contracts.contract_digest(
        selected_result
    )


def test_generic_schema_boundary_rejects_unknown_raw_fields_and_secrets() -> None:
    persisted = envelope().to_dict()
    persisted["prompt"] = "do the work"
    with pytest.raises(contracts.ContractError, match="unknown=.*prompt"):
        contracts.DelegationEnvelope.from_dict(persisted)
    with pytest.raises(contracts.ContractError, match="forbidden"):
        contracts.canonical_json({"rawResponse": "provider body"})
    with pytest.raises(contracts.ContractError, match="secret policy"):
        contracts.detached_json_copy(
            {"note": "api_key=abcdefghijklmnop"}
        )


@pytest.mark.parametrize(
    "unsafe_run_id",
    ["run/../../owner", "run:alternate-stream", "CON", "NUL.txt"],
)
def test_storage_identifiers_cannot_escape_or_alias_roots(
    unsafe_run_id: str,
) -> None:
    with pytest.raises(
        contracts.ContractError, match="safe storage|reserved Windows"
    ):
        envelope(run_id=unsafe_run_id)


def test_profile_invariants_partition_duration_usage_and_cost() -> None:
    with pytest.raises(contracts.ContractError, match="duration denominator"):
        contracts.CapabilityProfile(
            provider="openai",
            model="gpt-5.6-sol",
            role="implementer",
            task_class="backend-contract",
            sample_count=1,
            completed_count=1,
            observation_count=1,
            accepted_count=1,
            verification_pass_count=1,
        )
    with pytest.raises(contracts.ContractError, match="sample_count"):
        contracts.CapabilityProfile(
            provider="openai",
            model="gpt-5.6-sol",
            role="implementer",
            task_class="backend-contract",
            sample_count=1,
            completed_count=1,
            duration_by_status=(
                contracts.StatusDurationAggregate("completed", 1, 10),
            ),
        )
