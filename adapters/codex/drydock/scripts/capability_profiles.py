#!/usr/bin/env python3
"""Frozen/shadow/verified-commit capability evidence for Drydock."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from delegation_contracts import (
    SCHEMA_VERSION,
    CapabilityProfile,
    ContractError,
    DelegationEnvelope,
    DelegationResult,
    OutcomeObservation,
    strict_json_loads,
    validate_digest,
    validate_identifier,
    validate_reference,
    validate_storage_component,
    validate_timestamp,
)
from delegation_ledger import (
    INTEGRITY_LIMITATIONS,
    MAX_RECORDS,
    exclusive_file_lock,
    utc_now,
)


COMMIT_FIELDS = frozenset(
    {
        "schema_version",
        "sequence",
        "run_id",
        "recorded_at",
        "terminal_status",
        "start_state_digest",
        "state_digest",
        "observation_ids",
        "verification_ref",
        "profiles",
        "previous_record_digest",
        "record_digest",
    }
)
MAX_PROFILE_COUNT = 256
MAX_COMMIT_OBSERVATIONS = 512
MAX_PROFILE_LINE_BYTES = 512 * 1024
MAX_PROFILE_LOG_BYTES = 128 * 1024 * 1024


class ProfileError(RuntimeError):
    """Capability evidence could not be reduced or safely committed."""


def _canonical_profile_json(value: object) -> str:
    try:
        raw = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ContractError(
            "profile document is not canonical JSON: {}".format(exc)
        ) from exc
    if len(raw.encode("utf-8")) > MAX_PROFILE_LINE_BYTES:
        raise ContractError("profile document exceeds the byte bound")
    return raw


def _profile_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_profile_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ProfileSnapshot:
    profiles: Tuple[CapabilityProfile, ...]
    content_digest: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ContractError("unsupported profile snapshot schema")
        if not isinstance(self.profiles, (list, tuple)):
            raise ContractError("profile snapshot profiles must be an array")
        normalized_profiles = tuple(self.profiles)
        if any(
            not isinstance(profile, CapabilityProfile)
            for profile in normalized_profiles
        ):
            raise ContractError(
                "profile snapshot contains a non-profile value"
            )
        object.__setattr__(self, "profiles", normalized_profiles)
        if len(normalized_profiles) > MAX_PROFILE_COUNT:
            raise ContractError("profile snapshot exceeds the profile bound")
        keys = [profile.key for profile in normalized_profiles]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ContractError(
                "profile snapshot keys must be sorted and unique"
            )
        validate_digest(self.content_digest, "content_digest")
        if self.content_digest != _profile_digest(self.content_dict()):
            raise ContractError("profile snapshot digest does not match content")

    @classmethod
    def from_profiles(
        cls, profiles: Sequence[CapabilityProfile]
    ) -> "ProfileSnapshot":
        if not isinstance(profiles, (list, tuple)):
            raise ContractError("profiles must be an array")
        if any(not isinstance(profile, CapabilityProfile) for profile in profiles):
            raise ContractError("profiles contains a non-profile value")
        ordered = tuple(sorted(profiles, key=lambda profile: profile.key))
        content = {
            "schema_version": SCHEMA_VERSION,
            "profiles": [profile.to_dict() for profile in ordered],
        }
        return cls(profiles=ordered, content_digest=_profile_digest(content))

    @classmethod
    def empty(cls) -> "ProfileSnapshot":
        return cls.from_profiles(())

    @classmethod
    def from_dict(cls, value: object) -> "ProfileSnapshot":
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "content_digest",
            "profiles",
        }:
            raise ContractError("ProfileSnapshot fields do not match the schema")
        profiles = value["profiles"]
        if not isinstance(profiles, list):
            raise ContractError("ProfileSnapshot.profiles must be an array")
        if len(profiles) > MAX_PROFILE_COUNT:
            raise ContractError("ProfileSnapshot exceeds the profile bound")
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            profiles=tuple(
                CapabilityProfile.from_dict(profile) for profile in profiles
            ),
            content_digest=value["content_digest"],  # type: ignore[arg-type]
        )

    def content_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profiles": [profile.to_dict() for profile in self.profiles],
        }

    def to_dict(self) -> Dict[str, object]:
        value = self.content_dict()
        value["content_digest"] = self.content_digest
        return value

    def by_key(self) -> Dict[str, CapabilityProfile]:
        return {profile.key: profile for profile in self.profiles}


@dataclass(frozen=True)
class ShadowReduction:
    snapshot: ProfileSnapshot
    observation_ids: Tuple[str, ...]
    start_content_digest: str
    samples: Tuple[
        Tuple[DelegationEnvelope, DelegationResult, OutcomeObservation], ...
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ProfileSnapshot):
            raise ProfileError("shadow snapshot must be a ProfileSnapshot")
        validate_digest(self.start_content_digest, "start_content_digest")
        if not isinstance(self.observation_ids, (list, tuple)):
            raise ProfileError("shadow observation IDs must be an array")
        normalized_observation_ids = tuple(self.observation_ids)
        object.__setattr__(
            self, "observation_ids", normalized_observation_ids
        )
        if not normalized_observation_ids:
            raise ProfileError("shadow reduction must contain observations")
        if len(normalized_observation_ids) > MAX_COMMIT_OBSERVATIONS:
            raise ProfileError("shadow reduction exceeds the observation bound")
        if len(normalized_observation_ids) != len(
            set(normalized_observation_ids)
        ):
            raise ProfileError("shadow reduction contains duplicate observations")
        for observation_id in normalized_observation_ids:
            validate_identifier(observation_id, "observation_id")
        if not isinstance(self.samples, (list, tuple)):
            raise ProfileError("shadow samples must be an array")
        normalized_samples = _normalize_samples(self.samples)
        object.__setattr__(self, "samples", normalized_samples)
        if len(normalized_samples) != len(normalized_observation_ids):
            raise ProfileError(
                "shadow samples do not match the observation count"
            )


def _increment(
    profile: CapabilityProfile,
    result: DelegationResult,
    observation: OutcomeObservation,
) -> CapabilityProfile:
    value = profile.to_dict()
    value["sample_count"] += 1  # type: ignore[operator]
    value["observation_count"] += 1  # type: ignore[operator]
    value["duration_sample_count"] += 1  # type: ignore[operator]
    value["total_duration_ms"] += result.duration_ms  # type: ignore[operator]

    status_fields = {
        "completed": "completed_count",
        "failed": "failed_count",
        "timeout": "timeout_count",
        "cancelled": "cancelled_count",
        "invalid_output": "invalid_output_count",
        "unavailable": "unavailable_count",
    }
    outcome_fields = {
        "accepted": "accepted_count",
        "revision_required": "revision_required_count",
        "rejected": "rejected_count",
        "unavailable": "observation_unavailable_count",
    }
    verification_fields = {
        "pass": "verification_pass_count",
        "fail": "verification_fail_count",
        "not_run": "verification_not_run_count",
        "unavailable": "verification_unavailable_count",
    }
    for field in (
        status_fields[result.status],
        outcome_fields[observation.outcome],
        verification_fields[observation.verification],
    ):
        value[field] += 1  # type: ignore[operator]

    value["peer_findings_count"] += observation.peer_findings_count  # type: ignore[operator]
    value["blocking_findings_count"] += observation.blocking_findings_count  # type: ignore[operator]
    value["regression_count"] += observation.regression_count  # type: ignore[operator]
    if result.total_tokens is not None:
        value["token_sample_count"] += 1  # type: ignore[operator]
        value["total_tokens"] += result.total_tokens  # type: ignore[operator]
    return CapabilityProfile.from_dict(value)


def _normalize_samples(
    samples: Sequence[
        Tuple[DelegationEnvelope, DelegationResult, OutcomeObservation]
    ],
) -> Tuple[
    Tuple[DelegationEnvelope, DelegationResult, OutcomeObservation], ...
]:
    if not isinstance(samples, (list, tuple)):
        raise ProfileError("shadow samples must be an array")
    if not samples:
        raise ProfileError("shadow reduction requires at least one sample")
    if len(samples) > MAX_COMMIT_OBSERVATIONS:
        raise ProfileError("shadow reduction exceeds the observation bound")
    normalized: List[
        Tuple[DelegationEnvelope, DelegationResult, OutcomeObservation]
    ] = []
    seen: set = set()
    for sample in samples:
        if not isinstance(sample, (list, tuple)) or len(sample) != 3:
            raise ProfileError("each shadow sample must contain three contracts")
        envelope, result, observation = sample
        if (
            not isinstance(envelope, DelegationEnvelope)
            or not isinstance(result, DelegationResult)
            or not isinstance(observation, OutcomeObservation)
        ):
            raise ProfileError("shadow sample contains an invalid contract type")
        if (
            envelope.delegation_id != result.delegation_id
            or envelope.delegation_id != observation.delegation_id
        ):
            raise ProfileError("sample delegation identifiers do not match")
        if observation.observation_id in seen:
            raise ProfileError("duplicate observation in shadow batch")
        seen.add(observation.observation_id)
        normalized.append((envelope, result, observation))
    return tuple(normalized)


def _reduce_samples(
    start: ProfileSnapshot,
    samples: Sequence[
        Tuple[DelegationEnvelope, DelegationResult, OutcomeObservation]
    ],
) -> Tuple[ProfileSnapshot, Tuple[str, ...]]:
    profiles = start.by_key()
    observation_ids: List[str] = []
    for envelope, result, observation in samples:
        observation_ids.append(observation.observation_id)
        key = "|".join(
            (
                envelope.provider,
                envelope.model,
                envelope.role,
                envelope.task_class,
            )
        )
        current = profiles.get(
            key,
            CapabilityProfile(
                provider=envelope.provider,
                model=envelope.model,
                role=envelope.role,
                task_class=envelope.task_class,
            ),
        )
        profiles[key] = _increment(current, result, observation)
    return (
        ProfileSnapshot.from_profiles(tuple(profiles.values())),
        tuple(observation_ids),
    )


def shadow_reduce(
    start: ProfileSnapshot,
    samples: Sequence[
        Tuple[DelegationEnvelope, DelegationResult, OutcomeObservation]
    ],
) -> ShadowReduction:
    """Purely reduce unique samples into a new snapshot, leaving start frozen."""
    if not isinstance(start, ProfileSnapshot):
        raise ProfileError("start must be a ProfileSnapshot")
    normalized_samples = _normalize_samples(samples)
    snapshot, observation_ids = _reduce_samples(start, normalized_samples)
    return ShadowReduction(
        snapshot=snapshot,
        observation_ids=observation_ids,
        start_content_digest=start.content_digest,
        samples=normalized_samples,
    )


def _validate_shadow_transition(
    start: ProfileSnapshot, shadow: ShadowReduction
) -> Tuple[ProfileSnapshot, Tuple[str, ...]]:
    if shadow.start_content_digest != start.content_digest:
        raise ProfileError("shadow reduction does not match the frozen start")
    recomputed_snapshot, recomputed_ids = _reduce_samples(
        start, shadow.samples
    )
    if recomputed_ids != shadow.observation_ids:
        raise ProfileError(
            "shadow observation IDs do not match the source samples"
        )
    if recomputed_snapshot != shadow.snapshot:
        raise ProfileError(
            "shadow snapshot does not match the exact source reduction"
        )
    return recomputed_snapshot, recomputed_ids


def _integrity_report(
    *,
    valid: bool,
    record_count: int,
    last_record_digest: Optional[str],
    state_digest: str,
    corruption: Optional[Mapping[str, object]],
) -> Dict[str, object]:
    return {
        "valid": valid,
        "record_count": record_count,
        "last_record_digest": last_record_digest,
        "state_digest": state_digest,
        "corruption": dict(corruption) if corruption is not None else None,
        "authenticity": "not_established",
        "suffix_completeness": "not_established",
        "limitations": list(INTEGRITY_LIMITATIONS),
    }


def _validate_commit(
    value: object,
    *,
    expected_sequence: int,
    expected_start_digest: str,
    expected_previous_digest: Optional[str],
    seen_observation_ids: set,
) -> Tuple[Mapping[str, object], ProfileSnapshot]:
    if not isinstance(value, dict) or set(value) != COMMIT_FIELDS:
        raise ProfileError("profile commit fields do not match the schema")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != SCHEMA_VERSION
    ):
        raise ProfileError("unsupported profile commit schema")
    sequence = value["sequence"]
    if isinstance(sequence, bool) or sequence != expected_sequence:
        raise ProfileError("profile commit sequence is not contiguous")
    validate_storage_component(value["run_id"], "run_id")
    validate_timestamp(value["recorded_at"], "recorded_at")
    if value["terminal_status"] != "verified":
        raise ProfileError("persisted profile commit is not verified")
    if value["start_state_digest"] != expected_start_digest:
        raise ProfileError("profile commit start state does not match prior state")
    validate_digest(value["state_digest"], "state_digest")
    observation_ids = value["observation_ids"]
    if not isinstance(observation_ids, list) or not observation_ids:
        raise ProfileError("profile commit must contain observations")
    if len(observation_ids) > MAX_COMMIT_OBSERVATIONS:
        raise ProfileError("profile commit exceeds the observation bound")
    for observation_id in observation_ids:
        validate_identifier(observation_id, "observation_id")
        if observation_id in seen_observation_ids:
            raise ProfileError("observation_id was already committed")
        seen_observation_ids.add(observation_id)
    validate_reference(value["verification_ref"], "verification_ref")
    profiles = value["profiles"]
    if not isinstance(profiles, list):
        raise ProfileError("profile commit profiles must be an array")
    snapshot = ProfileSnapshot.from_profiles(
        tuple(CapabilityProfile.from_dict(profile) for profile in profiles)
    )
    if snapshot.content_digest != value["state_digest"]:
        raise ProfileError("profile commit state digest does not match profiles")
    if value["previous_record_digest"] != expected_previous_digest:
        raise ProfileError("profile commit chain predecessor does not match")
    if expected_previous_digest is not None:
        validate_digest(expected_previous_digest, "previous_record_digest")
    record_digest = validate_digest(value["record_digest"], "record_digest")
    unsigned = dict(value)
    del unsigned["record_digest"]
    if _profile_digest(unsigned) != record_digest:
        raise ProfileError("profile commit record digest does not match")
    return value, snapshot


def _read_commits_unlocked(
    path: Path,
) -> tuple[
    List[Mapping[str, object]],
    ProfileSnapshot,
    set,
    Dict[str, object],
]:
    empty = ProfileSnapshot.empty()
    if not path.exists():
        return [], empty, set(), _integrity_report(
            valid=True,
            record_count=0,
            last_record_digest=None,
            state_digest=empty.content_digest,
            corruption=None,
        )
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ProfileError("could not stat profile log: {}".format(exc)) from exc
    if size > MAX_PROFILE_LOG_BYTES:
        return [], empty, set(), _integrity_report(
            valid=False,
            record_count=0,
            last_record_digest=None,
            state_digest=empty.content_digest,
            corruption={"line": None, "reason": "profile log exceeds byte bound"},
        )

    commits: List[Mapping[str, object]] = []
    snapshot = empty
    previous_digest: Optional[str] = None
    seen_observations: set = set()
    try:
        with path.open("rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                if line_number > MAX_RECORDS:
                    return commits, snapshot, seen_observations, _integrity_report(
                        valid=False,
                        record_count=len(commits),
                        last_record_digest=previous_digest,
                        state_digest=snapshot.content_digest,
                        corruption={
                            "line": line_number,
                            "reason": "profile log exceeds record bound",
                        },
                    )
                if len(raw_line) > MAX_PROFILE_LINE_BYTES:
                    return commits, snapshot, seen_observations, _integrity_report(
                        valid=False,
                        record_count=len(commits),
                        last_record_digest=previous_digest,
                        state_digest=snapshot.content_digest,
                        corruption={
                            "line": line_number,
                            "reason": "profile line exceeds byte bound",
                        },
                    )
                if not raw_line.endswith(b"\n"):
                    return commits, snapshot, seen_observations, _integrity_report(
                        valid=False,
                        record_count=len(commits),
                        last_record_digest=previous_digest,
                        state_digest=snapshot.content_digest,
                        corruption={
                            "line": line_number,
                            "reason": "profile line is not newline-terminated",
                        },
                    )
                try:
                    parsed = strict_json_loads(raw_line[:-1].decode("utf-8"))
                    commit, next_snapshot = _validate_commit(
                        parsed,
                        expected_sequence=line_number,
                        expected_start_digest=snapshot.content_digest,
                        expected_previous_digest=previous_digest,
                        seen_observation_ids=seen_observations,
                    )
                except (
                    UnicodeDecodeError,
                    ContractError,
                    ProfileError,
                ) as exc:
                    return commits, snapshot, seen_observations, _integrity_report(
                        valid=False,
                        record_count=len(commits),
                        last_record_digest=previous_digest,
                        state_digest=snapshot.content_digest,
                        corruption={"line": line_number, "reason": str(exc)},
                    )
                commits.append(commit)
                snapshot = next_snapshot
                previous_digest = commit["record_digest"]  # type: ignore[assignment]
    except OSError as exc:
        raise ProfileError("could not read profile log: {}".format(exc)) from exc

    return commits, snapshot, seen_observations, _integrity_report(
        valid=True,
        record_count=len(commits),
        last_record_digest=previous_digest,
        state_digest=snapshot.content_digest,
        corruption=None,
    )


class CapabilityProfileStore:
    """Append-only controller-asserted snapshots with optimistic concurrency.

    This store validates the state transition and requires the controller to
    record a ``verified`` terminal assertion plus an evidence reference. It
    does not itself prove that the referenced artifact exists, passed, or came
    from an independent process.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = self.root / "profile-commits.jsonl"
        self.lock_path = self.root / ".profile-commits.lock"

    def verify(self) -> Dict[str, object]:
        with exclusive_file_lock(self.lock_path):
            _, _, _, report = _read_commits_unlocked(self.path)
        return report

    def current_snapshot(self) -> ProfileSnapshot:
        with exclusive_file_lock(self.lock_path):
            _, snapshot, _, report = _read_commits_unlocked(self.path)
        if not report["valid"]:
            raise ProfileError(
                "profile log is corrupt: {}".format(report["corruption"])
            )
        return snapshot

    def commit(
        self,
        *,
        run_id: str,
        start: ProfileSnapshot,
        shadow: ShadowReduction,
        terminal_status: str,
        verification_ref: str,
        recorded_at: Optional[str] = None,
    ) -> Mapping[str, object]:
        validate_storage_component(run_id, "run_id")
        if terminal_status != "verified":
            raise ProfileError(
                "profile learning requires terminal_status exactly verified"
            )
        selected_ref = validate_reference(
            verification_ref, "verification_ref"
        )
        selected_time = recorded_at or utc_now()
        validate_timestamp(selected_time, "recorded_at")
        if not isinstance(start, ProfileSnapshot):
            raise ProfileError("start must be a ProfileSnapshot")
        if not isinstance(shadow, ShadowReduction):
            raise ProfileError("shadow must be a ShadowReduction")

        self.root.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(self.lock_path):
            commits, current, seen, report = _read_commits_unlocked(self.path)
            if not report["valid"]:
                raise ProfileError(
                    "existing profile log is corrupt: {}".format(
                        report["corruption"]
                    )
                )
            if current.content_digest != start.content_digest:
                raise ProfileError(
                    "profile state conflict: current state advanced after run start"
                )
            validated_snapshot, validated_ids = _validate_shadow_transition(
                start, shadow
            )
            if validated_snapshot.content_digest == start.content_digest:
                raise ProfileError(
                    "shadow snapshot contains no learned state change"
                )
            repeated = sorted(set(validated_ids) & seen)
            if repeated:
                raise ProfileError(
                    "observations were already committed: {}".format(repeated)
                )
            previous_digest = report["last_record_digest"]
            commit: Dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "sequence": len(commits) + 1,
                "run_id": run_id,
                "recorded_at": selected_time,
                "terminal_status": terminal_status,
                "start_state_digest": start.content_digest,
                "state_digest": validated_snapshot.content_digest,
                "observation_ids": list(validated_ids),
                "verification_ref": selected_ref,
                "profiles": [
                    profile.to_dict() for profile in validated_snapshot.profiles
                ],
                "previous_record_digest": previous_digest,
            }
            commit["record_digest"] = _profile_digest(commit)
            raw = _canonical_profile_json(commit).encode("utf-8") + b"\n"
            if len(raw) > MAX_PROFILE_LINE_BYTES:
                raise ContractError("profile commit line exceeds the byte bound")
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size + len(raw) > MAX_PROFILE_LOG_BYTES:
                raise ProfileError("profile log would exceed the byte bound")
            try:
                with self.path.open("ab") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise ProfileError(
                    "could not append profile log: {}".format(exc)
                ) from exc
        return commit
