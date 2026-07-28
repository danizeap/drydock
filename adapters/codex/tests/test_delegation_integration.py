from __future__ import annotations

import os
from pathlib import Path

import pytest

from adapters.codex.drydock.scripts import capability_profiles
from adapters.codex.drydock.scripts import delegation_contracts as contracts
from adapters.codex.drydock.scripts import delegation_ledger


NOW = "2026-07-28T12:00:00.000Z"
DIGEST_A = "sha256:" + "a" * 64


def test_contract_ledger_profile_later_conflict_rebuild_and_repair(
    tmp_path: Path,
) -> None:
    selected_envelope = contracts.DelegationEnvelope.create(
        delegation_id="delegation-integration",
        run_id="run-integration",
        task_id="task-integration",
        task_class="backend-contract",
        role="implementer",
        provider="openai",
        model="gpt-5.6-sol",
        reasoning_effort="high",
        permission_profile="workspace-write",
        attempt=1,
        max_attempts=1,
        objective="Exercise the complete schema-v2 evidence path.",
        input_digests=(DIGEST_A,),
        capacity_snapshot_digest=None,
        policy_revision="policy-2",
        created_at=NOW,
    )
    selected_result = contracts.DelegationResult(
        delegation_id=selected_envelope.delegation_id,
        run_id=selected_envelope.run_id,
        runtime_status="completed",
        duration_ms=1234,
        usage_basis="provider_reported",
        input_tokens=100,
        cached_input_tokens=20,
        output_tokens=50,
        reasoning_tokens=10,
        reasoning_token_semantics="included_in_output",
        total_tokens=150,
        cost_basis="provider_reported",
        cost_microusd=2500,
        artifact_refs=("artifacts/integration.patch",),
        evidence_refs=("evidence/integration.json",),
        error_code=None,
        untrusted_claimed_terminal_status="completed",
        untrusted_error_summary=None,
        completed_at=NOW,
    )

    def observed(observation_id: str, observer_kind: str):
        return contracts.OutcomeObservation(
            observation_id=observation_id,
            delegation_id=selected_envelope.delegation_id,
            run_id=selected_envelope.run_id,
            envelope_digest=contracts.contract_digest(selected_envelope),
            result_digest=contracts.contract_digest(selected_result),
            observer_kind=observer_kind,
            outcome="accepted",
            verification="pass",
            peer_findings_count=1,
            blocking_findings_count=0,
            regression_count=0,
            evidence_refs=(
                "verification/{}.json".format(observation_id),
            ),
            observed_at=NOW,
        )

    run_ledger = delegation_ledger.RunLedger(
        tmp_path / "ledger", selected_envelope.run_id
    )
    run_ledger.append(
        event_type="delegation_contract_bound",
        runtime_status="started",
        payload={
            "envelope_digest": contracts.contract_digest(selected_envelope),
            "request_binding_digest": (
                selected_envelope.request_binding_digest
            ),
        },
        delegation_id=selected_envelope.delegation_id,
        task_id=selected_envelope.task_id,
        event_id="event-start",
        recorded_at=NOW,
    )
    run_ledger.append(
        event_type="delegation_result_bound",
        runtime_status=selected_result.runtime_status,
        payload={"result_digest": contracts.contract_digest(selected_result)},
        delegation_id=selected_envelope.delegation_id,
        task_id=selected_envelope.task_id,
        event_id="event-result",
        recorded_at=NOW,
    )
    assert run_ledger.verify()["valid"] is True

    store = capability_profiles.CapabilityProfileStore(tmp_path / "profiles")
    start = store.current_snapshot()
    first = observed("peer-observation", "peer")
    first_shadow = capability_profiles.shadow_reduce(
        start, [(selected_envelope, selected_result, first)]
    )
    store.commit_reduction(
        commit_run_id="profile-run-1",
        start=start,
        shadow=first_shadow,
        controller_asserted_status="passed",
        asserted_verification_ref="verification/profile-run-1.json",
        recorded_at=NOW,
    )

    current = store.current_snapshot()
    later = observed("verifier-observation", "verifier")
    later_shadow = capability_profiles.shadow_reduce(
        current, [(selected_envelope, selected_result, later)]
    )
    store.commit_reduction(
        commit_run_id="profile-run-2",
        start=current,
        shadow=later_shadow,
        controller_asserted_status="passed",
        asserted_verification_ref="verification/profile-run-2.json",
        recorded_at=NOW,
    )

    current = store.current_snapshot()
    conflict_shadow = capability_profiles.shadow_reduce(
        current, [(selected_envelope, selected_result, later)]
    )
    conflict_commit = store.commit_reduction(
        commit_run_id="profile-run-3",
        start=current,
        shadow=conflict_shadow,
        controller_asserted_status="passed",
        asserted_verification_ref="verification/profile-run-3.json",
        recorded_at=NOW,
    )
    assert conflict_commit["decisions"][0]["disposition"] == "rejected"
    assert conflict_commit["decisions"][0]["reasons"] == [
        "duplicate_observation_id"
    ]
    rebuilt = store.rebuild_snapshot()
    profile = rebuilt.profiles[0]
    assert profile.sample_count == 1
    assert profile.observation_count == 2
    assert profile.duplicate_observation_id_count == 1
    assert rebuilt == store.current_snapshot()

    with run_ledger.path.open("ab") as stream:
        stream.write(b'{"schema_version":2,"sequence":3,"event_id":"torn')
        stream.flush()
        os.fsync(stream.fileno())
    expected_digest = contracts.digest_bytes(run_ledger.path.read_bytes())
    with pytest.raises(delegation_ledger.RepairInterrupted):
        run_ledger.repair_torn_tail(
            expected_digest=expected_digest,
            _fault_after="post_intent",
        )
    repair = run_ledger.repair_torn_tail(
        expected_digest=expected_digest
    )
    assert repair["status"] == "repaired"
    report = run_ledger.verify()
    assert report["valid"] is True
    assert report["has_repair_history"] is True
    assert run_ledger.read_records()[-1]["event_type"] == (
        delegation_ledger.REPAIR_EVENT_TYPE
    )
    replay = run_ledger.repair_torn_tail(
        expected_digest=expected_digest
    )
    assert replay["status"] == "completed_replay"
