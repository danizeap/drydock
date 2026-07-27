from __future__ import annotations

import copy

import pytest

import delegation_contracts as contracts


NOW = "2026-07-27T12:00:00.000Z"
DIGEST_A = "sha256:" + "a" * 64


def envelope(objective: str = "Implement the bounded adapter.") -> contracts.DelegationEnvelope:
    return contracts.DelegationEnvelope.create(
        delegation_id="delegation-1",
        run_id="run-1",
        task_id="task-1",
        task_class="backend-contract",
        role="implementer",
        provider="openai",
        model="gpt-5.6-sol",
        reasoning_effort="high",
        permission_profile="workspace-write",
        attempt=1,
        max_attempts=2,
        objective=objective,
        input_digests=(DIGEST_A,),
        capacity_snapshot_digest=None,
        policy_revision="policy-1",
        created_at=NOW,
    )


def result(**overrides: object) -> contracts.DelegationResult:
    values = {
        "delegation_id": "delegation-1",
        "status": "completed",
        "duration_ms": 1200,
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "output_tokens": 40,
        "total_tokens": 140,
        "artifact_refs": ("changes/run-1.patch",),
        "evidence_refs": ("verification/run-1.json",),
        "error_code": None,
        "error_summary": None,
        "completed_at": NOW,
    }
    values.update(overrides)
    return contracts.DelegationResult(**values)  # type: ignore[arg-type]


def test_envelope_persists_digests_and_never_raw_objective() -> None:
    first = envelope("A private runtime objective.")
    second = envelope("A private runtime objective.")
    persisted = first.to_dict()

    assert "objective" not in persisted
    assert persisted["objective_digest"] == contracts.digest_text(
        "A private runtime objective."
    )
    assert first.idempotency_key == second.idempotency_key
    assert "private runtime objective" not in contracts.canonical_json(persisted)


def test_envelope_rejects_unknown_or_raw_prompt_field() -> None:
    persisted = envelope().to_dict()
    persisted["prompt"] = "do the work"
    with pytest.raises(contracts.ContractError, match="unknown=.*prompt"):
        contracts.DelegationEnvelope.from_dict(persisted)

    with pytest.raises(contracts.ContractError, match="forbidden"):
        contracts.canonical_json({"prompt": "do the work"})
    with pytest.raises(contracts.ContractError, match="forbidden"):
        contracts.canonical_json({"rawResponse": "provider body"})


@pytest.mark.parametrize(
    "unsafe_run_id",
    ["run/../../owner", "run:alternate-stream", "CON", "NUL.txt"],
)
def test_identifiers_cannot_escape_or_alias_storage_roots(
    unsafe_run_id: str,
) -> None:
    persisted = envelope().to_dict()
    persisted["run_id"] = unsafe_run_id
    with pytest.raises(
        contracts.ContractError,
        match="safe storage|reserved Windows",
    ):
        contracts.DelegationEnvelope.from_dict(persisted)


def test_idempotency_binds_execution_fields_and_rejects_tampering() -> None:
    original = envelope()
    changed = contracts.DelegationEnvelope.create(
        delegation_id="delegation-1",
        run_id="run-1",
        task_id="task-1",
        task_class="backend-contract",
        role="implementer",
        provider="openai",
        model="gpt-5.6-sol",
        reasoning_effort="xhigh",
        permission_profile="workspace-write",
        attempt=1,
        max_attempts=2,
        objective="Implement the bounded adapter.",
        input_digests=(DIGEST_A,),
        capacity_snapshot_digest=None,
        policy_revision="policy-1",
        created_at=NOW,
    )
    assert changed.idempotency_key != original.idempotency_key

    persisted = original.to_dict()
    persisted["permission_profile"] = "read-only"
    with pytest.raises(contracts.ContractError, match="idempotency_key"):
        contracts.DelegationEnvelope.from_dict(persisted)


def test_strict_json_rejects_duplicates_and_nonfinite_numbers() -> None:
    with pytest.raises(contracts.ContractError, match="duplicate JSON key"):
        contracts.strict_json_loads('{"status":"ok","status":"failed"}')
    with pytest.raises(contracts.ContractError, match="non-finite"):
        contracts.strict_json_loads('{"duration":NaN}')
    with pytest.raises(contracts.ContractError, match="non-finite"):
        contracts.canonical_json({"duration": float("inf")})


def test_partial_usage_remains_unknown() -> None:
    partial = result(
        status="failed",
        input_tokens=100,
        cached_input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        error_code="provider_failure",
        error_summary="provider returned no terminal usage",
    )
    assert partial.to_dict()["usage"]["total_tokens"] is None  # type: ignore[index]

    with pytest.raises(contracts.ContractError, match="partial usage"):
        result(
            status="failed",
            input_tokens=100,
            cached_input_tokens=None,
            output_tokens=None,
            total_tokens=100,
            error_code="provider_failure",
            error_summary="missing output count",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"duration_ms": True}, "duration_ms"),
        ({"total_tokens": 141}, "does not match"),
        ({"cached_input_tokens": 101}, "cannot exceed"),
        ({"artifact_refs": ("../owner/.env",)}, "safe relative"),
        ({"artifact_refs": ("evidence/result.json:stream",)}, "unsafe path"),
        ({"artifact_refs": ("evidence/NUL.txt",)}, "reserved Windows"),
        (
            {
                "status": "failed",
                "error_code": "provider_failure",
                "error_summary": "api_key=abcdefghijklmnop",
            },
            "secret policy",
        ),
    ],
)
def test_result_rejects_inconsistent_or_sensitive_evidence(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(contracts.ContractError, match=message):
        result(**overrides)


def test_contract_round_trips_are_strict_and_content_stable() -> None:
    original = envelope()
    persisted = copy.deepcopy(original.to_dict())
    restored = contracts.DelegationEnvelope.from_dict(persisted)
    assert restored == original
    assert restored.to_dict() == persisted

    normalized_result = result()
    assert (
        contracts.DelegationResult.from_dict(normalized_result.to_dict())
        == normalized_result
    )


def test_contracts_detach_from_caller_owned_mutable_lists() -> None:
    refs = ["verification/original.json"]
    normalized = result(
        artifact_refs=[],
        evidence_refs=refs,
    )
    refs[0] = "C:/owner/.env"
    refs.append("../outside")

    assert normalized.evidence_refs == ("verification/original.json",)
    assert normalized.to_dict()["evidence_refs"] == [
        "verification/original.json"
    ]
    assert isinstance(normalized.evidence_refs, tuple)


def test_profile_cannot_carry_authority_fields_or_inconsistent_counts() -> None:
    profile = contracts.CapabilityProfile(
        provider="openai",
        model="gpt-5.6-sol",
        role="implementer",
        task_class="backend-contract",
    )
    persisted = profile.to_dict()
    assert not {
        "trust",
        "score",
        "permissions",
        "authority",
        "gate_status",
    } & set(persisted)

    persisted["authority"] = "allow"
    with pytest.raises(contracts.ContractError, match="unknown=.*authority"):
        contracts.CapabilityProfile.from_dict(persisted)

    with pytest.raises(contracts.ContractError, match="status counts"):
        contracts.CapabilityProfile(
            provider="openai",
            model="gpt-5.6-sol",
            role="implementer",
            task_class="backend-contract",
            sample_count=1,
            duration_sample_count=1,
        )


def test_per_observation_counts_and_usage_have_operational_bounds() -> None:
    with pytest.raises(contracts.ContractError, match="configured bound"):
        result(duration_ms=contracts.MAX_DURATION_MS + 1)
    with pytest.raises(contracts.ContractError, match="configured bound"):
        contracts.OutcomeObservation(
            observation_id="observation-1",
            delegation_id="delegation-1",
            observer_kind="verifier",
            outcome="accepted",
            verification="pass",
            peer_findings_count=contracts.MAX_FINDINGS_PER_OBSERVATION + 1,
            blocking_findings_count=0,
            regression_count=0,
            evidence_refs=("verification/result.json",),
            observed_at=NOW,
        )
