from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from adapters.codex.drydock.scripts import capability_profiles
from adapters.codex.drydock.scripts import delegation_contracts as contracts


NOW = "2026-07-28T12:00:00.000Z"
DIGEST_A = "sha256:" + "a" * 64


def envelope(
    delegation_id: str = "delegation-1",
    *,
    run_id: str = "run-1",
    provider: str = "openai",
    model: str = "gpt-5.6-sol",
    role: str = "implementer",
    task_class: str = "backend-contract",
    objective: str = "Implement a bounded local contract.",
) -> contracts.DelegationEnvelope:
    return contracts.DelegationEnvelope.create(
        delegation_id=delegation_id,
        run_id=run_id,
        task_id="task-" + delegation_id,
        task_class=task_class,
        role=role,
        provider=provider,
        model=model,
        reasoning_effort="high",
        permission_profile="workspace-write",
        attempt=1,
        max_attempts=1,
        objective=objective,
        input_digests=(DIGEST_A,),
        capacity_snapshot_digest=None,
        policy_revision="policy-2",
        created_at=NOW,
    )


def result(
    selected_envelope: contracts.DelegationEnvelope,
    *,
    runtime_status: str = "completed",
    duration_ms: int = 2000,
    usage_basis: str = "provider_reported",
    reasoning_semantics: str = "included_in_output",
    cost_basis: str = "provider_reported",
) -> contracts.DelegationResult:
    failed = runtime_status != "completed"
    reasoning_tokens = 10
    total_tokens = (
        150 if reasoning_semantics == "excluded_from_output" else 140
    )
    return contracts.DelegationResult(
        delegation_id=selected_envelope.delegation_id,
        run_id=selected_envelope.run_id,
        runtime_status=runtime_status,
        duration_ms=duration_ms,
        usage_basis=usage_basis,
        input_tokens=100,
        cached_input_tokens=10,
        output_tokens=40,
        reasoning_tokens=reasoning_tokens,
        reasoning_token_semantics=reasoning_semantics,
        total_tokens=total_tokens,
        cost_basis=cost_basis,
        cost_microusd=2000,
        artifact_refs=(
            "artifacts/{}.patch".format(selected_envelope.delegation_id),
        ),
        evidence_refs=(
            "evidence/{}.json".format(selected_envelope.delegation_id),
        ),
        error_code="execution_failed" if failed else None,
        untrusted_claimed_terminal_status=(
            "failed" if failed else "completed"
        ),
        untrusted_error_summary=(
            {"message": "executor returned a bounded failure"}
            if failed
            else None
        ),
        completed_at=NOW,
    )


def observation(
    selected_envelope: contracts.DelegationEnvelope,
    selected_result: contracts.DelegationResult,
    *,
    observation_id: str = "observation-1",
    observer_kind: str = "verifier",
    outcome: str = "accepted",
    verification: str = "pass",
    peer_findings_count: int = 2,
    blocking_findings_count: int = 0,
    regression_count: int = 0,
    run_id: Optional[str] = None,
    envelope_digest: Optional[str] = None,
    result_digest: Optional[str] = None,
) -> contracts.OutcomeObservation:
    return contracts.OutcomeObservation(
        observation_id=observation_id,
        delegation_id=selected_envelope.delegation_id,
        run_id=run_id or selected_envelope.run_id,
        envelope_digest=(
            envelope_digest or contracts.contract_digest(selected_envelope)
        ),
        result_digest=(
            result_digest or contracts.contract_digest(selected_result)
        ),
        observer_kind=observer_kind,
        outcome=outcome,
        verification=verification,
        peer_findings_count=peer_findings_count,
        blocking_findings_count=blocking_findings_count,
        regression_count=regression_count,
        evidence_refs=(
            "verification/{}.json".format(observation_id),
        ),
        observed_at=NOW,
    )


def one_submission(
    delegation_id: str = "delegation-1",
    observation_id: str = "observation-1",
):
    selected_envelope = envelope(delegation_id)
    selected_result = result(selected_envelope)
    return (
        selected_envelope,
        selected_result,
        observation(
            selected_envelope,
            selected_result,
            observation_id=observation_id,
        ),
    )


def commit(
    store: capability_profiles.CapabilityProfileStore,
    start: capability_profiles.ProfileSnapshot,
    shadow: capability_profiles.ShadowReduction,
    run_id: str = "profile-run-1",
):
    return store.commit_reduction(
        commit_run_id=run_id,
        start=start,
        shadow=shadow,
        claimed_terminal_status="verified",
        untrusted_verification_ref="verification/{}.json".format(run_id),
        recorded_at=NOW,
    )


def test_one_execution_many_initial_observations_counts_sample_once() -> None:
    start = capability_profiles.ProfileSnapshot.empty()
    selected_envelope = envelope()
    selected_result = result(selected_envelope)
    first = observation(
        selected_envelope,
        selected_result,
        observation_id="peer-observation",
        observer_kind="peer",
        peer_findings_count=2,
    )
    second = observation(
        selected_envelope,
        selected_result,
        observation_id="verifier-observation",
        observer_kind="verifier",
        peer_findings_count=1,
        regression_count=1,
    )
    shadow = capability_profiles.shadow_reduce(
        start,
        [
            (selected_envelope, selected_result, first),
            (selected_envelope, selected_result, second),
        ],
    )
    profile = shadow.snapshot.profiles[0]

    assert [item.disposition for item in shadow.decisions] == [
        "accepted_sample",
        "accepted_observation",
    ]
    assert profile.sample_count == 1
    assert profile.completed_count == 1
    assert profile.observation_count == 2
    assert profile.accepted_count == 2
    assert profile.peer_findings_count == 3
    assert profile.regression_count == 1
    assert profile.duration_by_status == (
        contracts.StatusDurationAggregate("completed", 1, 2000),
    )
    assert len(profile.token_usage_by_status_and_basis) == 1
    assert profile.token_usage_by_status_and_basis[0].sample_count == 1
    assert len(profile.cost_by_status_and_basis) == 1
    assert profile.cost_by_status_and_basis[0].sample_count == 1


def test_later_observation_changes_only_observation_domain(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    first_source = one_submission()
    first_shadow = capability_profiles.shadow_reduce(start, [first_source])
    commit(store, start, first_shadow)

    current = store.current_snapshot()
    selected_envelope, selected_result, _ = first_source
    later = observation(
        selected_envelope,
        selected_result,
        observation_id="later-peer",
        observer_kind="peer",
        outcome="revision_required",
        verification="not_run",
        peer_findings_count=4,
    )
    later_shadow = capability_profiles.shadow_reduce(
        current, [(selected_envelope, selected_result, later)]
    )
    before_profile = current.profiles[0]
    after_profile = later_shadow.snapshot.profiles[0]

    assert later_shadow.decisions[0].disposition == "accepted_observation"
    assert after_profile.sample_count == before_profile.sample_count == 1
    assert after_profile.completed_count == before_profile.completed_count == 1
    assert after_profile.duration_by_status == before_profile.duration_by_status
    assert (
        after_profile.token_usage_by_status_and_basis
        == before_profile.token_usage_by_status_and_basis
    )
    assert (
        after_profile.cost_by_status_and_basis
        == before_profile.cost_by_status_and_basis
    )
    assert after_profile.observation_count == 2
    assert after_profile.revision_required_count == 1
    assert after_profile.peer_findings_count == 6

    commit(store, current, later_shadow, "profile-run-2")
    assert store.rebuild_snapshot() == later_shadow.snapshot


def test_same_batch_duplicate_and_result_conflict_are_durable() -> None:
    start = capability_profiles.ProfileSnapshot.empty()
    first = one_submission()
    selected_envelope, selected_result, selected_observation = first
    changed_result = result(selected_envelope, duration_ms=3000)
    changed_observation = observation(
        selected_envelope,
        changed_result,
        observation_id="conflicting-result",
    )
    shadow = capability_profiles.shadow_reduce(
        start,
        [
            first,
            first,
            (selected_envelope, changed_result, changed_observation),
        ],
    )
    profile = shadow.snapshot.profiles[0]

    assert [item.disposition for item in shadow.decisions] == [
        "accepted_sample",
        "rejected",
        "rejected",
    ]
    assert shadow.decisions[1].reasons == ("duplicate_observation_id",)
    assert "delegation_id_conflict" in shadow.decisions[2].reasons
    assert "result_digest_conflict" in shadow.decisions[2].reasons
    assert profile.sample_count == 1
    assert profile.observation_count == 1
    assert profile.duplicate_observation_id_count == 1
    assert profile.delegation_id_conflict_count == 1
    assert profile.result_digest_conflict_count == 1


def test_cross_commit_duplicate_and_observation_content_conflict_persist(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    first = one_submission()
    commit(
        store,
        start,
        capability_profiles.shadow_reduce(start, [first]),
    )

    current = store.current_snapshot()
    duplicate_shadow = capability_profiles.shadow_reduce(current, [first])
    duplicate_commit = commit(
        store, current, duplicate_shadow, "profile-run-2"
    )
    assert duplicate_commit["decisions"][0]["reasons"] == [
        "duplicate_observation_id"
    ]

    current = store.current_snapshot()
    selected_envelope, selected_result, _ = first
    conflicting_observation = observation(
        selected_envelope,
        selected_result,
        observation_id="observation-1",
        outcome="rejected",
        verification="fail",
    )
    conflict_shadow = capability_profiles.shadow_reduce(
        current,
        [(selected_envelope, selected_result, conflicting_observation)],
    )
    conflict_commit = commit(
        store, current, conflict_shadow, "profile-run-3"
    )
    assert conflict_commit["decisions"][0]["reasons"] == [
        "observation_content_conflict"
    ]
    profile = store.current_snapshot().profiles[0]
    assert profile.sample_count == 1
    assert profile.observation_count == 1
    assert profile.duplicate_observation_id_count == 1
    assert profile.observation_content_conflict_count == 1
    assert store.rebuild_snapshot() == store.current_snapshot()


def test_cross_commit_run_envelope_result_conflicts_use_original_profile(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    first = one_submission()
    commit(
        store,
        start,
        capability_profiles.shadow_reduce(start, [first]),
    )

    current = store.current_snapshot()
    conflicting_envelope = envelope(
        "delegation-1",
        run_id="run-2",
        task_class="different-class",
        objective="Different request binding.",
    )
    conflicting_result = result(conflicting_envelope, duration_ms=4000)
    conflicting_observation = observation(
        conflicting_envelope,
        conflicting_result,
        observation_id="conflicting-binding",
    )
    shadow = capability_profiles.shadow_reduce(
        current,
        [
            (
                conflicting_envelope,
                conflicting_result,
                conflicting_observation,
            )
        ],
    )
    decision = shadow.decisions[0]

    assert decision.disposition == "rejected"
    assert decision.profile_key == current.profiles[0].key
    assert set(decision.reasons) == {
        "delegation_id_conflict",
        "run_id_conflict",
        "envelope_digest_conflict",
        "result_digest_conflict",
    }
    commit(store, current, shadow, "profile-run-2")
    profile = store.current_snapshot().profiles[0]
    assert profile.sample_count == 1
    assert profile.run_id_conflict_count == 1
    assert profile.envelope_digest_conflict_count == 1
    assert profile.result_digest_conflict_count == 1


def test_duration_token_and_cost_aggregates_never_mix_status_or_basis() -> None:
    start = capability_profiles.ProfileSnapshot.empty()
    completed_envelope = envelope("completed-delegation")
    completed_result = result(completed_envelope)
    failed_envelope = envelope("failed-delegation")
    failed_result = result(
        failed_envelope,
        runtime_status="failed",
        duration_ms=5000,
        usage_basis="provider_estimated",
        reasoning_semantics="excluded_from_output",
        cost_basis="provider_estimated",
    )
    shadow = capability_profiles.shadow_reduce(
        start,
        [
            (
                completed_envelope,
                completed_result,
                observation(
                    completed_envelope,
                    completed_result,
                    observation_id="completed-observation",
                ),
            ),
            (
                failed_envelope,
                failed_result,
                observation(
                    failed_envelope,
                    failed_result,
                    observation_id="failed-observation",
                    outcome="rejected",
                    verification="fail",
                ),
            ),
        ],
    )
    profile = shadow.snapshot.profiles[0]
    durations = {
        item.runtime_status: (item.sample_count, item.total_duration_ms)
        for item in profile.duration_by_status
    }
    usage_keys = {
        (item.runtime_status, item.usage_basis, item.reasoning_token_semantics)
        for item in profile.token_usage_by_status_and_basis
    }
    cost_keys = {
        (item.runtime_status, item.cost_basis)
        for item in profile.cost_by_status_and_basis
    }

    assert durations == {"completed": (1, 2000), "failed": (1, 5000)}
    assert usage_keys == {
        ("completed", "provider_reported", "included_in_output"),
        ("failed", "provider_estimated", "excluded_from_output"),
    }
    assert cost_keys == {
        ("completed", "provider_reported"),
        ("failed", "provider_estimated"),
    }


def test_store_persists_full_sources_and_rebuilds_byte_for_byte(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    source = one_submission()
    shadow = capability_profiles.shadow_reduce(start, [source])
    persisted = commit(store, start, shadow)

    assert persisted["source_submissions"] == [
        {
            "envelope": source[0].to_dict(),
            "result": source[1].to_dict(),
            "observation": source[2].to_dict(),
        }
    ]
    assert persisted["decisions"][0]["disposition"] == "accepted_sample"
    rebuilt = store.rebuild_snapshot()
    assert rebuilt == shadow.snapshot
    assert (
        capability_profiles._canonical_profile_json(rebuilt.to_dict())
        == capability_profiles._canonical_profile_json(
            store.current_snapshot().to_dict()
        )
    )


def test_profile_commit_round_trips_nested_untrusted_error_claim(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    selected_envelope = envelope("failed-nested")
    selected_result = result(
        selected_envelope,
        runtime_status="failed",
    )
    nested_value = selected_result.to_dict()
    nested_value["untrusted_error_summary"] = {
        "details": [{"code": "bounded", "retryable": False}]
    }
    selected_result = contracts.DelegationResult.from_dict(nested_value)
    selected_observation = observation(
        selected_envelope,
        selected_result,
        outcome="rejected",
        verification="fail",
    )
    shadow = capability_profiles.shadow_reduce(
        start,
        [(selected_envelope, selected_result, selected_observation)],
    )
    commit(store, start, shadow)

    assert store.verify()["valid"] is True
    assert (
        store.read_commits()[0]["source_submissions"][0]["result"][
            "untrusted_error_summary"
        ]
        == {"details": [{"code": "bounded", "retryable": False}]}
    )


def test_profile_snapshot_can_exceed_generic_array_bound_within_schema_limit(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    first_batch = []
    for number in range(capability_profiles.MAX_COMMIT_SUBMISSIONS):
        selected_envelope = envelope(
            "delegation-{}".format(number),
            task_class="class-{}".format(number),
        )
        selected_result = result(selected_envelope)
        first_batch.append(
            (
                selected_envelope,
                selected_result,
                observation(
                    selected_envelope,
                    selected_result,
                    observation_id="observation-{}".format(number),
                ),
            )
        )
    first_shadow = capability_profiles.shadow_reduce(start, first_batch)
    commit(store, start, first_shadow)

    current = store.current_snapshot()
    final_envelope = envelope("delegation-64", task_class="class-64")
    final_result = result(final_envelope)
    final_shadow = capability_profiles.shadow_reduce(
        current,
        [
            (
                final_envelope,
                final_result,
                observation(
                    final_envelope,
                    final_result,
                    observation_id="observation-64",
                ),
            )
        ],
    )
    commit(store, current, final_shadow, "profile-run-2")

    assert len(store.current_snapshot().profiles) == 65
    assert store.verify()["valid"] is True


def test_profile_replay_detects_tampered_source_or_decision(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    commit(
        store,
        start,
        capability_profiles.shadow_reduce(start, [one_submission()]),
    )
    value = json.loads(store.path.read_text(encoding="utf-8"))
    value["decisions"][0]["disposition"] = "accepted_observation"
    store.path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    report = store.verify()
    assert report["valid"] is False
    assert "decisions do not match" in report["corruption"]["reason"]


def test_profile_modules_bind_package_qualified_siblings() -> None:
    assert (
        capability_profiles.contracts.__name__
        == "adapters.codex.drydock.scripts.delegation_contracts"
    )
    assert (
        capability_profiles.ledger.__name__
        == "adapters.codex.drydock.scripts.delegation_ledger"
    )


def test_untrusted_claim_gate_and_stale_state_fail_before_append(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    shadow = capability_profiles.shadow_reduce(start, [one_submission()])
    with pytest.raises(capability_profiles.ProfileError, match="exactly verified"):
        store.commit_reduction(
            commit_run_id="profile-run-1",
            start=start,
            shadow=shadow,
            claimed_terminal_status="implemented",
            untrusted_verification_ref="verification/run.json",
        )
    with pytest.raises(contracts.ContractError, match="relative"):
        store.commit_reduction(
            commit_run_id="profile-run-1",
            start=start,
            shadow=shadow,
            claimed_terminal_status="verified",
            untrusted_verification_ref="C:/owner/result.json",
        )
    assert not store.path.exists()

    commit(store, start, shadow)
    stale_shadow = capability_profiles.shadow_reduce(
        start, [one_submission("delegation-2", "observation-2")]
    )
    before = store.path.read_bytes()
    with pytest.raises(capability_profiles.ProfileError, match="conflict"):
        commit(store, start, stale_shadow, "profile-run-2")
    assert store.path.read_bytes() == before


def test_store_recomputes_and_refuses_forged_snapshot(tmp_path: Path) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    legitimate = capability_profiles.shadow_reduce(start, [one_submission()])
    profile_value = legitimate.snapshot.profiles[0].to_dict()
    profile_value["peer_findings_count"] = 999
    forged_profile = contracts.CapabilityProfile.from_dict(profile_value)
    forged_snapshot = capability_profiles.ProfileSnapshot.from_parts(
        [forged_profile],
        legitimate.snapshot.delegation_bindings,
        legitimate.snapshot.observation_bindings,
    )
    forged = capability_profiles.ShadowReduction(
        snapshot=forged_snapshot,
        start_content_digest=legitimate.start_content_digest,
        submissions=legitimate.submissions,
        decisions=legitimate.decisions,
    )

    with pytest.raises(capability_profiles.ProfileError, match="exact source"):
        commit(store, start, forged)
    assert not store.path.exists()


def test_read_only_profile_calls_do_not_create_lock_or_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "absent"
    store = capability_profiles.CapabilityProfileStore(root)
    before = list(tmp_path.rglob("*"))

    assert store.verify()["valid"] is True
    assert store.current_snapshot() == capability_profiles.ProfileSnapshot.empty()
    assert store.read_commits() == []
    assert list(tmp_path.rglob("*")) == before
    assert not store.lock_path.exists()
    assert not root.exists()


def test_v1_profile_commit_is_explicitly_corrupt(tmp_path: Path) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    commit(
        store,
        start,
        capability_profiles.shadow_reduce(start, [one_submission()]),
    )
    value = json.loads(store.path.read_text(encoding="utf-8"))
    value["schema_version"] = 1
    store.path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    report = store.verify()
    assert report["valid"] is False
    assert "v2 required" in report["corruption"]["reason"]
    with pytest.raises(capability_profiles.ProfileError, match="corrupt"):
        store.current_snapshot()
