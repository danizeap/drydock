from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

import capability_profiles
import delegation_contracts as contracts


NOW = "2026-07-27T12:00:00.000Z"
DIGEST_A = "sha256:" + "a" * 64


def envelope(
    delegation_id: str = "delegation-1",
    *,
    provider: str = "openai",
    model: str = "gpt-5.6-sol",
    role: str = "implementer",
    task_class: str = "backend-contract",
) -> contracts.DelegationEnvelope:
    return contracts.DelegationEnvelope.create(
        delegation_id=delegation_id,
        run_id="run-1",
        task_id="task-" + delegation_id,
        task_class=task_class,
        role=role,
        provider=provider,
        model=model,
        reasoning_effort="high",
        permission_profile="workspace-write",
        attempt=1,
        max_attempts=1,
        objective="Implement a bounded local contract.",
        input_digests=(DIGEST_A,),
        capacity_snapshot_digest=None,
        policy_revision="policy-1",
        created_at=NOW,
    )


def result(
    delegation_id: str = "delegation-1",
    *,
    status: str = "completed",
    total_tokens: Optional[int] = 150,
) -> contracts.DelegationResult:
    failed = status != "completed"
    return contracts.DelegationResult(
        delegation_id=delegation_id,
        status=status,
        duration_ms=2000,
        input_tokens=100 if total_tokens is not None else None,
        cached_input_tokens=10 if total_tokens is not None else None,
        output_tokens=50 if total_tokens is not None else None,
        total_tokens=total_tokens,
        artifact_refs=("artifacts/{}.patch".format(delegation_id),),
        evidence_refs=("evidence/{}.json".format(delegation_id),),
        error_code="execution_failed" if failed else None,
        error_summary="executor returned a bounded failure" if failed else None,
        completed_at=NOW,
    )


def observation(
    delegation_id: str = "delegation-1",
    *,
    observation_id: str = "observation-1",
    outcome: str = "accepted",
    verification: str = "pass",
) -> contracts.OutcomeObservation:
    return contracts.OutcomeObservation(
        observation_id=observation_id,
        delegation_id=delegation_id,
        observer_kind="verifier",
        outcome=outcome,
        verification=verification,
        peer_findings_count=2,
        blocking_findings_count=0,
        regression_count=0,
        evidence_refs=("verification/{}.json".format(observation_id),),
        observed_at=NOW,
    )


def reduced(
    start: Optional[capability_profiles.ProfileSnapshot] = None,
    *,
    delegation_id: str = "delegation-1",
    observation_id: str = "observation-1",
) -> capability_profiles.ShadowReduction:
    selected_start = start or capability_profiles.ProfileSnapshot.empty()
    return capability_profiles.shadow_reduce(
        selected_start,
        [
            (
                envelope(delegation_id),
                result(delegation_id),
                observation(
                    delegation_id, observation_id=observation_id
                ),
            )
        ],
    )


def test_shadow_reduction_preserves_frozen_start_and_tracks_raw_counts() -> None:
    start = capability_profiles.ProfileSnapshot.empty()
    start_bytes = contracts.canonical_json(start.to_dict())
    shadow = reduced(start)

    assert contracts.canonical_json(start.to_dict()) == start_bytes
    assert start.profiles == ()
    assert shadow.snapshot.content_digest != start.content_digest
    profile = shadow.snapshot.profiles[0]
    assert profile.sample_count == 1
    assert profile.completed_count == 1
    assert profile.accepted_count == 1
    assert profile.verification_pass_count == 1
    assert profile.peer_findings_count == 2
    assert profile.token_sample_count == 1
    assert profile.total_tokens == 150
    assert profile.duration_sample_count == 1
    assert profile.total_duration_ms == 2000
    assert not hasattr(profile, "trust")
    assert not hasattr(profile, "authority")


def test_profiles_are_task_and_role_specific() -> None:
    start = capability_profiles.ProfileSnapshot.empty()
    shadow = capability_profiles.shadow_reduce(
        start,
        [
            (envelope("d-1"), result("d-1"), observation("d-1", observation_id="o-1")),
            (
                envelope("d-2", role="reviewer"),
                result("d-2"),
                observation("d-2", observation_id="o-2"),
            ),
            (
                envelope("d-3", task_class="frontend"),
                result("d-3"),
                observation("d-3", observation_id="o-3"),
            ),
        ],
    )
    assert len(shadow.snapshot.profiles) == 3
    assert {profile.role for profile in shadow.snapshot.profiles} == {
        "implementer",
        "reviewer",
    }
    assert {profile.task_class for profile in shadow.snapshot.profiles} == {
        "backend-contract",
        "frontend",
    }


def test_duplicate_or_mismatched_observations_fail_closed() -> None:
    item = (
        envelope("d-1"),
        result("d-1"),
        observation("d-1", observation_id="same"),
    )
    with pytest.raises(capability_profiles.ProfileError, match="duplicate"):
        capability_profiles.shadow_reduce(
            capability_profiles.ProfileSnapshot.empty(), [item, item]
        )
    with pytest.raises(capability_profiles.ProfileError, match="do not match"):
        capability_profiles.shadow_reduce(
            capability_profiles.ProfileSnapshot.empty(),
            [
                (
                    envelope("d-1"),
                    result("d-2"),
                    observation("d-1"),
                )
            ],
        )


def test_unverified_or_unsafe_commit_never_creates_profile_log(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    shadow = reduced(start)
    with pytest.raises(capability_profiles.ProfileError, match="exactly verified"):
        store.commit(
            run_id="run-1",
            start=start,
            shadow=shadow,
            terminal_status="implemented",
            verification_ref="verification/run-1.json",
        )
    with pytest.raises(contracts.ContractError, match="relative"):
        store.commit(
            run_id="run-1",
            start=start,
            shadow=shadow,
            terminal_status="verified",
            verification_ref="C:/owner/verification.json",
        )
    assert not store.path.exists()


def test_verified_commit_round_trips_and_retains_integrity_disclosures(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    shadow = reduced(start)
    commit = store.commit(
        run_id="run-1",
        start=start,
        shadow=shadow,
        terminal_status="verified",
        verification_ref="verification/run-1.json",
        recorded_at=NOW,
    )

    assert commit["start_state_digest"] == start.content_digest
    assert commit["state_digest"] == shadow.snapshot.content_digest
    assert store.current_snapshot() == shadow.snapshot
    report = store.verify()
    assert report["valid"] is True
    assert report["record_count"] == 1
    assert report["authenticity"] == "not_established"
    assert report["suffix_completeness"] == "not_established"
    assert "user-writable" in " ".join(report["limitations"])


def test_optimistic_conflict_refuses_stale_run(tmp_path: Path) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    common_start = store.current_snapshot()
    first = reduced(
        common_start,
        delegation_id="d-1",
        observation_id="o-1",
    )
    stale = reduced(
        common_start,
        delegation_id="d-2",
        observation_id="o-2",
    )
    store.commit(
        run_id="run-1",
        start=common_start,
        shadow=first,
        terminal_status="verified",
        verification_ref="verification/run-1.json",
    )
    before = store.path.read_bytes()
    with pytest.raises(capability_profiles.ProfileError, match="conflict"):
        store.commit(
            run_id="run-2",
            start=common_start,
            shadow=stale,
            terminal_status="verified",
            verification_ref="verification/run-2.json",
        )
    assert store.path.read_bytes() == before


def test_replayed_observation_and_tampered_commit_are_rejected(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    first = reduced(start, observation_id="replayed-observation")
    store.commit(
        run_id="run-1",
        start=start,
        shadow=first,
        terminal_status="verified",
        verification_ref="verification/run-1.json",
        recorded_at=NOW,
    )
    current = store.current_snapshot()
    replay = reduced(
        current,
        delegation_id="delegation-2",
        observation_id="replayed-observation",
    )
    with pytest.raises(capability_profiles.ProfileError, match="already committed"):
        store.commit(
            run_id="run-2",
            start=current,
            shadow=replay,
            terminal_status="verified",
            verification_ref="verification/run-2.json",
        )

    record = json.loads(store.path.read_text(encoding="utf-8"))
    record["profiles"][0]["accepted_count"] = 99
    store.path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    report = store.verify()
    assert report["valid"] is False
    assert report["corruption"]["line"] == 1
    with pytest.raises(capability_profiles.ProfileError, match="corrupt"):
        store.current_snapshot()


def test_profile_commit_supports_bounded_multi_class_history(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    samples = []
    for number in range(30):
        delegation_id = "delegation-{}".format(number)
        samples.append(
            (
                envelope(
                    delegation_id,
                    task_class="task-class-{}".format(number),
                ),
                result(delegation_id),
                observation(
                    delegation_id,
                    observation_id="observation-{}".format(number),
                ),
            )
        )
    shadow = capability_profiles.shadow_reduce(start, samples)
    assert len(shadow.snapshot.profiles) == 30
    assert len(
        capability_profiles._canonical_profile_json(
            shadow.snapshot.content_dict()
        ).encode("utf-8")
    ) > contracts.MAX_CANONICAL_BYTES

    store.commit(
        run_id="run-large",
        start=start,
        shadow=shadow,
        terminal_status="verified",
        verification_ref="verification/run-large.json",
    )
    assert len(store.current_snapshot().profiles) == 30


def test_store_recomputes_and_refuses_forged_monotonic_aggregates(
    tmp_path: Path,
) -> None:
    store = capability_profiles.CapabilityProfileStore(tmp_path)
    start = store.current_snapshot()
    legitimate = reduced(start)
    forged = capability_profiles.ShadowReduction(
        snapshot=capability_profiles.ProfileSnapshot.from_profiles(
            [
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
                    peer_findings_count=999,
                    token_sample_count=1,
                    total_tokens=999_999,
                    duration_sample_count=1,
                    total_duration_ms=999_999,
                )
            ]
        ),
        observation_ids=legitimate.observation_ids,
        start_content_digest=start.content_digest,
        samples=legitimate.samples,
    )
    with pytest.raises(capability_profiles.ProfileError, match="exact source"):
        store.commit(
            run_id="run-forged",
            start=start,
            shadow=forged,
            terminal_status="verified",
            verification_ref="verification/run-forged.json",
        )
    assert not store.path.exists()


def test_snapshots_and_shadow_ids_detach_from_caller_lists() -> None:
    profile = contracts.CapabilityProfile(
        provider="openai",
        model="gpt-5.6-sol",
        role="implementer",
        task_class="backend-contract",
    )
    profiles = [profile]
    snapshot = capability_profiles.ProfileSnapshot.from_profiles(profiles)
    profiles.clear()
    assert snapshot.profiles == (profile,)

    legitimate = reduced(capability_profiles.ProfileSnapshot.empty())
    ids = list(legitimate.observation_ids)
    detached = capability_profiles.ShadowReduction(
        snapshot=legitimate.snapshot,
        observation_ids=ids,
        start_content_digest=legitimate.start_content_digest,
        samples=list(legitimate.samples),
    )
    ids[0] = "mutated"
    assert detached.observation_ids == ("observation-1",)
