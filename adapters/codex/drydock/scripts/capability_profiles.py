#!/usr/bin/env python3
"""Replayable schema-v2 capability evidence for Drydock delegation."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from . import delegation_contracts as contracts
from . import delegation_ledger as ledger


MAX_PROFILE_COUNT = 256
MAX_COMMIT_SUBMISSIONS = 64
MAX_PROFILE_COMMITS = 32
MAX_PROFILE_LINE_BYTES = 4 * 1024 * 1024
MAX_PROFILE_LOG_BYTES = 128 * 1024 * 1024

COMMIT_FIELDS = frozenset(
    {
        "schema_version",
        "sequence",
        "commit_run_id",
        "recorded_at",
        "claimed_terminal_status",
        "untrusted_verification_ref",
        "start_state_digest",
        "state_digest",
        "source_submissions",
        "decisions",
        "profiles",
        "delegation_bindings",
        "observation_bindings",
        "previous_record_digest",
        "record_digest",
    }
)
DECISION_FIELDS = frozenset(
    {
        "submission_index",
        "disposition",
        "reasons",
        "profile_key",
        "delegation_id",
        "observation_id",
        "run_id",
        "envelope_digest",
        "result_digest",
        "observation_digest",
    }
)
DECISION_DISPOSITIONS = frozenset(
    {"accepted_sample", "accepted_observation", "rejected"}
)
REASON_TO_COUNTER = {
    "duplicate_observation_id": "duplicate_observation_id_count",
    "delegation_id_conflict": "delegation_id_conflict_count",
    "run_id_conflict": "run_id_conflict_count",
    "envelope_digest_conflict": "envelope_digest_conflict_count",
    "result_digest_conflict": "result_digest_conflict_count",
    "observation_content_conflict": "observation_content_conflict_count",
}
STATUS_COUNT_FIELDS = {
    status: "{}_count".format(status) for status in contracts.RESULT_STATUSES
}
OUTCOME_COUNT_FIELDS = {
    "accepted": "accepted_count",
    "revision_required": "revision_required_count",
    "rejected": "rejected_count",
    "unavailable": "observation_unavailable_count",
}
VERIFICATION_COUNT_FIELDS = {
    "pass": "verification_pass_count",
    "fail": "verification_fail_count",
    "not_run": "verification_not_run_count",
    "unavailable": "verification_unavailable_count",
}


class ProfileError(RuntimeError):
    """Capability evidence could not be replayed or safely committed."""


def _canonical_profile_json(value: object) -> str:
    contracts.validate_json_structure(value)
    try:
        raw = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except RecursionError as exc:
        raise contracts.ContractError(
            "profile document exceeds the nesting bound"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise contracts.ContractError(
            "profile document is not canonical JSON: {}".format(exc)
        ) from exc
    if len(raw.encode("utf-8")) > MAX_PROFILE_LINE_BYTES - 1:
        raise contracts.ContractError("profile document exceeds the byte bound")
    return raw


def _profile_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_profile_json(value).encode("utf-8")
    ).hexdigest()


def _validate_profile_key(value: object, field: str = "profile_key") -> str:
    if not isinstance(value, str):
        raise ProfileError("{} must be text".format(field))
    parts = value.split("|")
    if len(parts) != 4:
        raise ProfileError("{} must contain four components".format(field))
    normalized = "|".join(
        contracts.validate_identifier(part, "{} component".format(field))
        for part in parts
    )
    if normalized != value:
        raise ProfileError("{} is not canonical".format(field))
    return value


@dataclass(frozen=True)
class DelegationBinding:
    delegation_id: str
    run_id: str
    envelope_digest: str
    result_digest: str
    profile_key: str

    def __post_init__(self) -> None:
        contracts.validate_identifier(self.delegation_id, "delegation_id")
        contracts.validate_storage_component(self.run_id, "run_id")
        contracts.validate_digest(self.envelope_digest, "envelope_digest")
        contracts.validate_digest(self.result_digest, "result_digest")
        _validate_profile_key(self.profile_key)

    @property
    def key(self) -> str:
        return self.delegation_id

    def to_dict(self) -> Dict[str, object]:
        return {
            "delegation_id": self.delegation_id,
            "run_id": self.run_id,
            "envelope_digest": self.envelope_digest,
            "result_digest": self.result_digest,
            "profile_key": self.profile_key,
        }

    @classmethod
    def from_dict(cls, value: object) -> "DelegationBinding":
        if not isinstance(value, dict) or set(value) != {
            "delegation_id",
            "run_id",
            "envelope_digest",
            "result_digest",
            "profile_key",
        }:
            raise ProfileError("DelegationBinding fields do not match schema")
        return cls(**value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ObservationBinding:
    observation_id: str
    delegation_id: str
    observation_digest: str

    def __post_init__(self) -> None:
        contracts.validate_identifier(self.observation_id, "observation_id")
        contracts.validate_identifier(self.delegation_id, "delegation_id")
        contracts.validate_digest(self.observation_digest, "observation_digest")

    @property
    def key(self) -> str:
        return self.observation_id

    def to_dict(self) -> Dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "delegation_id": self.delegation_id,
            "observation_digest": self.observation_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ObservationBinding":
        if not isinstance(value, dict) or set(value) != {
            "observation_id",
            "delegation_id",
            "observation_digest",
        }:
            raise ProfileError("ObservationBinding fields do not match schema")
        return cls(**value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ProfileSnapshot:
    profiles: Tuple[contracts.CapabilityProfile, ...]
    delegation_bindings: Tuple[DelegationBinding, ...]
    observation_bindings: Tuple[ObservationBinding, ...]
    content_digest: str
    schema_version: int = contracts.SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != contracts.SCHEMA_VERSION
        ):
            raise contracts.ContractError(
                "unsupported profile snapshot schema; v2 required"
            )
        profiles = self._normalize(
            self.profiles,
            contracts.CapabilityProfile,
            "profile snapshot profiles",
            MAX_PROFILE_COUNT,
        )
        delegations = self._normalize(
            self.delegation_bindings,
            DelegationBinding,
            "delegation bindings",
            MAX_PROFILE_COMMITS * MAX_COMMIT_SUBMISSIONS,
        )
        observations = self._normalize(
            self.observation_bindings,
            ObservationBinding,
            "observation bindings",
            MAX_PROFILE_COMMITS * MAX_COMMIT_SUBMISSIONS,
        )
        object.__setattr__(self, "profiles", profiles)
        object.__setattr__(self, "delegation_bindings", delegations)
        object.__setattr__(self, "observation_bindings", observations)
        profile_keys = {profile.key for profile in profiles}
        delegation_ids = {binding.delegation_id for binding in delegations}
        for binding in delegations:
            if binding.profile_key not in profile_keys:
                raise ProfileError(
                    "delegation binding points to an absent profile"
                )
        for binding in observations:
            if binding.delegation_id not in delegation_ids:
                raise ProfileError(
                    "observation binding points to an absent delegation"
                )
        contracts.validate_digest(self.content_digest, "content_digest")
        if self.content_digest != _profile_digest(self.content_dict()):
            raise contracts.ContractError(
                "profile snapshot digest does not match content"
            )

    @staticmethod
    def _normalize(
        values: object, expected_type: type, field: str, maximum: int
    ) -> tuple:
        if not isinstance(values, (list, tuple)):
            raise ProfileError("{} must be an array".format(field))
        normalized = tuple(values)
        if len(normalized) > maximum:
            raise ProfileError("{} exceeds the item bound".format(field))
        if any(not isinstance(item, expected_type) for item in normalized):
            raise ProfileError("{} contains an invalid value".format(field))
        keys = [item.key for item in normalized]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ProfileError("{} keys must be sorted and unique".format(field))
        return normalized

    @classmethod
    def from_parts(
        cls,
        profiles: Sequence[contracts.CapabilityProfile],
        delegation_bindings: Sequence[DelegationBinding],
        observation_bindings: Sequence[ObservationBinding],
    ) -> "ProfileSnapshot":
        ordered_profiles = tuple(sorted(profiles, key=lambda item: item.key))
        ordered_delegations = tuple(
            sorted(delegation_bindings, key=lambda item: item.key)
        )
        ordered_observations = tuple(
            sorted(observation_bindings, key=lambda item: item.key)
        )
        content = {
            "schema_version": contracts.SCHEMA_VERSION,
            "profiles": [item.to_dict() for item in ordered_profiles],
            "delegation_bindings": [
                item.to_dict() for item in ordered_delegations
            ],
            "observation_bindings": [
                item.to_dict() for item in ordered_observations
            ],
        }
        return cls(
            profiles=ordered_profiles,
            delegation_bindings=ordered_delegations,
            observation_bindings=ordered_observations,
            content_digest=_profile_digest(content),
        )

    @classmethod
    def empty(cls) -> "ProfileSnapshot":
        return cls.from_parts((), (), ())

    @classmethod
    def from_dict(cls, value: object) -> "ProfileSnapshot":
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "content_digest",
            "profiles",
            "delegation_bindings",
            "observation_bindings",
        }:
            raise contracts.ContractError(
                "ProfileSnapshot fields do not match schema"
            )
        for field in (
            "profiles",
            "delegation_bindings",
            "observation_bindings",
        ):
            if not isinstance(value[field], list):
                raise contracts.ContractError(
                    "ProfileSnapshot.{} must be an array".format(field)
                )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            content_digest=value["content_digest"],  # type: ignore[arg-type]
            profiles=tuple(
                contracts.CapabilityProfile.from_dict(item)
                for item in value["profiles"]
            ),
            delegation_bindings=tuple(
                DelegationBinding.from_dict(item)
                for item in value["delegation_bindings"]
            ),
            observation_bindings=tuple(
                ObservationBinding.from_dict(item)
                for item in value["observation_bindings"]
            ),
        )

    def content_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profiles": [item.to_dict() for item in self.profiles],
            "delegation_bindings": [
                item.to_dict() for item in self.delegation_bindings
            ],
            "observation_bindings": [
                item.to_dict() for item in self.observation_bindings
            ],
        }

    def to_dict(self) -> Dict[str, object]:
        value = self.content_dict()
        value["content_digest"] = self.content_digest
        return value

    def profiles_by_key(self) -> Dict[str, contracts.CapabilityProfile]:
        return {profile.key: profile for profile in self.profiles}

    def delegations_by_id(self) -> Dict[str, DelegationBinding]:
        return {
            binding.delegation_id: binding
            for binding in self.delegation_bindings
        }

    def observations_by_id(self) -> Dict[str, ObservationBinding]:
        return {
            binding.observation_id: binding
            for binding in self.observation_bindings
        }


@dataclass(frozen=True)
class SourceSubmission:
    envelope: contracts.DelegationEnvelope
    result: contracts.DelegationResult
    observation: contracts.OutcomeObservation

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, contracts.DelegationEnvelope):
            raise ProfileError("source envelope has an invalid type")
        if not isinstance(self.result, contracts.DelegationResult):
            raise ProfileError("source result has an invalid type")
        if not isinstance(self.observation, contracts.OutcomeObservation):
            raise ProfileError("source observation has an invalid type")
        # Round trips detach every retained source from caller-owned values.
        object.__setattr__(
            self,
            "envelope",
            contracts.DelegationEnvelope.from_dict(self.envelope.to_dict()),
        )
        object.__setattr__(
            self,
            "result",
            contracts.DelegationResult.from_dict(self.result.to_dict()),
        )
        object.__setattr__(
            self,
            "observation",
            contracts.OutcomeObservation.from_dict(self.observation.to_dict()),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "envelope": self.envelope.to_dict(),
            "result": self.result.to_dict(),
            "observation": self.observation.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "SourceSubmission":
        if not isinstance(value, dict) or set(value) != {
            "envelope",
            "result",
            "observation",
        }:
            raise ProfileError("source submission fields do not match schema")
        return cls(
            envelope=contracts.DelegationEnvelope.from_dict(value["envelope"]),
            result=contracts.DelegationResult.from_dict(value["result"]),
            observation=contracts.OutcomeObservation.from_dict(
                value["observation"]
            ),
        )


@dataclass(frozen=True)
class ReductionDecision:
    submission_index: int
    disposition: str
    reasons: Tuple[str, ...]
    profile_key: str
    delegation_id: str
    observation_id: str
    run_id: str
    envelope_digest: str
    result_digest: str
    observation_digest: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.submission_index, bool)
            or not isinstance(self.submission_index, int)
            or self.submission_index < 0
            or self.submission_index >= MAX_COMMIT_SUBMISSIONS
        ):
            raise ProfileError("decision submission_index is invalid")
        if self.disposition not in DECISION_DISPOSITIONS:
            raise ProfileError("decision disposition is invalid")
        if not isinstance(self.reasons, (list, tuple)):
            raise ProfileError("decision reasons must be an array")
        normalized_reasons = tuple(self.reasons)
        object.__setattr__(self, "reasons", normalized_reasons)
        if (
            normalized_reasons != tuple(
                reason
                for reason in contracts.CONFLICT_REASONS
                if reason in set(normalized_reasons)
            )
            or len(normalized_reasons) != len(set(normalized_reasons))
        ):
            raise ProfileError(
                "decision reasons must be unique and canonically ordered"
            )
        if (self.disposition == "rejected") != bool(normalized_reasons):
            raise ProfileError(
                "only rejected decisions may carry conflict reasons"
            )
        _validate_profile_key(self.profile_key)
        contracts.validate_identifier(self.delegation_id, "delegation_id")
        contracts.validate_identifier(self.observation_id, "observation_id")
        contracts.validate_storage_component(self.run_id, "run_id")
        for field in (
            "envelope_digest",
            "result_digest",
            "observation_digest",
        ):
            contracts.validate_digest(getattr(self, field), field)

    def to_dict(self) -> Dict[str, object]:
        return {
            "submission_index": self.submission_index,
            "disposition": self.disposition,
            "reasons": list(self.reasons),
            "profile_key": self.profile_key,
            "delegation_id": self.delegation_id,
            "observation_id": self.observation_id,
            "run_id": self.run_id,
            "envelope_digest": self.envelope_digest,
            "result_digest": self.result_digest,
            "observation_digest": self.observation_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ReductionDecision":
        if not isinstance(value, dict) or set(value) != DECISION_FIELDS:
            raise ProfileError("reduction decision fields do not match schema")
        normalized = dict(value)
        reasons = normalized["reasons"]
        if not isinstance(reasons, list):
            raise ProfileError("reduction decision reasons must be an array")
        normalized["reasons"] = tuple(reasons)
        return cls(**normalized)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ShadowReduction:
    snapshot: ProfileSnapshot
    start_content_digest: str
    submissions: Tuple[SourceSubmission, ...]
    decisions: Tuple[ReductionDecision, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ProfileSnapshot):
            raise ProfileError("shadow snapshot must be a ProfileSnapshot")
        contracts.validate_digest(
            self.start_content_digest, "start_content_digest"
        )
        submissions = _normalize_submissions(self.submissions)
        decisions = tuple(self.decisions)
        if any(not isinstance(item, ReductionDecision) for item in decisions):
            raise ProfileError("shadow decisions contain an invalid value")
        if len(submissions) != len(decisions):
            raise ProfileError(
                "shadow submissions do not match decision count"
            )
        object.__setattr__(self, "submissions", submissions)
        object.__setattr__(self, "decisions", decisions)


def _normalize_submissions(
    values: Sequence[object],
) -> Tuple[SourceSubmission, ...]:
    if not isinstance(values, (list, tuple)):
        raise ProfileError("source submissions must be an array")
    if not values:
        raise ProfileError("reduction requires at least one source submission")
    if len(values) > MAX_COMMIT_SUBMISSIONS:
        raise ProfileError("source submissions exceed the commit bound")
    normalized: List[SourceSubmission] = []
    for value in values:
        if isinstance(value, SourceSubmission):
            normalized.append(SourceSubmission.from_dict(value.to_dict()))
            continue
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ProfileError(
                "each source submission must contain envelope/result/observation"
            )
        normalized.append(
            SourceSubmission(
                envelope=value[0],  # type: ignore[arg-type]
                result=value[1],  # type: ignore[arg-type]
                observation=value[2],  # type: ignore[arg-type]
            )
        )
    return tuple(normalized)


def _profile_key(envelope: contracts.DelegationEnvelope) -> str:
    return "|".join(
        (
            envelope.provider,
            envelope.model,
            envelope.role,
            envelope.task_class,
        )
    )


def _increment_observation(
    profile: contracts.CapabilityProfile,
    observation: contracts.OutcomeObservation,
) -> contracts.CapabilityProfile:
    value = profile.to_dict()
    value["observation_count"] += 1  # type: ignore[operator]
    value[OUTCOME_COUNT_FIELDS[observation.outcome]] += 1  # type: ignore[operator]
    value[VERIFICATION_COUNT_FIELDS[observation.verification]] += 1  # type: ignore[operator]
    value["peer_findings_count"] += observation.peer_findings_count  # type: ignore[operator]
    value["blocking_findings_count"] += observation.blocking_findings_count  # type: ignore[operator]
    value["regression_count"] += observation.regression_count  # type: ignore[operator]
    return contracts.CapabilityProfile.from_dict(value)


def _increment_sample(
    profile: contracts.CapabilityProfile,
    result: contracts.DelegationResult,
    observation: contracts.OutcomeObservation,
) -> contracts.CapabilityProfile:
    value = profile.to_dict()
    value["sample_count"] += 1  # type: ignore[operator]
    value[STATUS_COUNT_FIELDS[result.runtime_status]] += 1  # type: ignore[operator]

    durations = {
        item["runtime_status"]: item
        for item in value["duration_by_status"]  # type: ignore[union-attr]
    }
    duration = durations.setdefault(
        result.runtime_status,
        {
            "runtime_status": result.runtime_status,
            "sample_count": 0,
            "total_duration_ms": 0,
        },
    )
    duration["sample_count"] += 1
    duration["total_duration_ms"] += result.duration_ms
    value["duration_by_status"] = sorted(
        durations.values(), key=lambda item: item["runtime_status"]
    )

    if result.total_tokens is not None:
        usage_key = "|".join(
            (
                result.runtime_status,
                result.usage_basis,
                result.reasoning_token_semantics,
            )
        )
        usage_values = {
            "|".join(
                (
                    item["runtime_status"],
                    item["usage_basis"],
                    item["reasoning_token_semantics"],
                )
            ): item
            for item in value["token_usage_by_status_and_basis"]  # type: ignore[union-attr]
        }
        usage = usage_values.setdefault(
            usage_key,
            {
                "runtime_status": result.runtime_status,
                "usage_basis": result.usage_basis,
                "reasoning_token_semantics": (
                    result.reasoning_token_semantics
                ),
                "sample_count": 0,
                "reasoning_token_sample_count": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_reasoning_tokens": 0,
                "total_tokens": 0,
            },
        )
        usage["sample_count"] += 1
        usage["total_input_tokens"] += result.input_tokens or 0
        usage["total_output_tokens"] += result.output_tokens or 0
        usage["total_tokens"] += result.total_tokens
        if result.reasoning_tokens is not None:
            usage["reasoning_token_sample_count"] += 1
            usage["total_reasoning_tokens"] += result.reasoning_tokens
        value["token_usage_by_status_and_basis"] = sorted(
            usage_values.values(),
            key=lambda item: "|".join(
                (
                    item["runtime_status"],
                    item["usage_basis"],
                    item["reasoning_token_semantics"],
                )
            ),
        )

    if result.cost_microusd is not None:
        cost_key = "|".join((result.runtime_status, result.cost_basis))
        cost_values = {
            "|".join((item["runtime_status"], item["cost_basis"])): item
            for item in value["cost_by_status_and_basis"]  # type: ignore[union-attr]
        }
        cost = cost_values.setdefault(
            cost_key,
            {
                "runtime_status": result.runtime_status,
                "cost_basis": result.cost_basis,
                "sample_count": 0,
                "total_cost_microusd": 0,
            },
        )
        cost["sample_count"] += 1
        cost["total_cost_microusd"] += result.cost_microusd
        value["cost_by_status_and_basis"] = sorted(
            cost_values.values(),
            key=lambda item: "|".join(
                (item["runtime_status"], item["cost_basis"])
            ),
        )
    value["observation_count"] += 1  # type: ignore[operator]
    value[OUTCOME_COUNT_FIELDS[observation.outcome]] += 1  # type: ignore[operator]
    value[VERIFICATION_COUNT_FIELDS[observation.verification]] += 1  # type: ignore[operator]
    value["peer_findings_count"] += observation.peer_findings_count  # type: ignore[operator]
    value["blocking_findings_count"] += observation.blocking_findings_count  # type: ignore[operator]
    value["regression_count"] += observation.regression_count  # type: ignore[operator]
    return contracts.CapabilityProfile.from_dict(value)


def _increment_rejection(
    profile: contracts.CapabilityProfile, reasons: Sequence[str]
) -> contracts.CapabilityProfile:
    value = profile.to_dict()
    for reason in reasons:
        value[REASON_TO_COUNTER[reason]] += 1  # type: ignore[operator]
    return contracts.CapabilityProfile.from_dict(value)


def _canonical_reasons(reasons: set) -> Tuple[str, ...]:
    return tuple(
        reason for reason in contracts.CONFLICT_REASONS if reason in reasons
    )


def _reduce_submissions(
    start: ProfileSnapshot,
    submissions: Sequence[SourceSubmission],
) -> Tuple[ProfileSnapshot, Tuple[ReductionDecision, ...]]:
    profiles = start.profiles_by_key()
    delegations = start.delegations_by_id()
    observations = start.observations_by_id()
    decisions: List[ReductionDecision] = []

    for index, submission in enumerate(submissions):
        envelope = submission.envelope
        result = submission.result
        observation = submission.observation
        envelope_digest = contracts.contract_digest(envelope)
        result_digest = contracts.contract_digest(result)
        observation_digest = contracts.contract_digest(observation)

        original = delegations.get(envelope.delegation_id)
        if original is None:
            original = delegations.get(result.delegation_id)
        if original is None:
            original = delegations.get(observation.delegation_id)
        existing_observation = observations.get(observation.observation_id)
        if original is None and existing_observation is not None:
            original = delegations.get(existing_observation.delegation_id)

        profile_key = original.profile_key if original else _profile_key(envelope)
        reasons: set = set()
        ids = {
            envelope.delegation_id,
            result.delegation_id,
            observation.delegation_id,
        }
        if len(ids) != 1:
            reasons.add("delegation_id_conflict")
        runs = {envelope.run_id, result.run_id, observation.run_id}
        if len(runs) != 1:
            reasons.add("run_id_conflict")
        if observation.envelope_digest != envelope_digest:
            reasons.add("envelope_digest_conflict")
        if observation.result_digest != result_digest:
            reasons.add("result_digest_conflict")

        if original is not None:
            if any(
                delegation_id != original.delegation_id
                for delegation_id in ids
            ):
                reasons.add("delegation_id_conflict")
            if any(run_id != original.run_id for run_id in runs):
                reasons.add("run_id_conflict")
            if envelope_digest != original.envelope_digest:
                reasons.add("envelope_digest_conflict")
                reasons.add("delegation_id_conflict")
            if result_digest != original.result_digest:
                reasons.add("result_digest_conflict")
                reasons.add("delegation_id_conflict")
            if observation.envelope_digest != original.envelope_digest:
                reasons.add("envelope_digest_conflict")
            if observation.result_digest != original.result_digest:
                reasons.add("result_digest_conflict")

        if existing_observation is not None:
            if (
                existing_observation.observation_digest == observation_digest
                and existing_observation.delegation_id
                == observation.delegation_id
            ):
                reasons.add("duplicate_observation_id")
            else:
                reasons.add("observation_content_conflict")
                if (
                    existing_observation.delegation_id
                    != observation.delegation_id
                ):
                    reasons.add("delegation_id_conflict")

        normalized_reasons = _canonical_reasons(reasons)
        profile = profiles.get(profile_key)
        if profile is None:
            profile = contracts.CapabilityProfile(
                provider=envelope.provider,
                model=envelope.model,
                role=envelope.role,
                task_class=envelope.task_class,
            )

        if normalized_reasons:
            disposition = "rejected"
            profiles[profile_key] = _increment_rejection(
                profile, normalized_reasons
            )
        elif original is None:
            disposition = "accepted_sample"
            binding = DelegationBinding(
                delegation_id=envelope.delegation_id,
                run_id=envelope.run_id,
                envelope_digest=envelope_digest,
                result_digest=result_digest,
                profile_key=profile_key,
            )
            delegations[binding.delegation_id] = binding
            observations[observation.observation_id] = ObservationBinding(
                observation_id=observation.observation_id,
                delegation_id=envelope.delegation_id,
                observation_digest=observation_digest,
            )
            profiles[profile_key] = _increment_sample(
                profile, result, observation
            )
        else:
            disposition = "accepted_observation"
            observations[observation.observation_id] = ObservationBinding(
                observation_id=observation.observation_id,
                delegation_id=original.delegation_id,
                observation_digest=observation_digest,
            )
            profiles[profile_key] = _increment_observation(
                profile, observation
            )

        decisions.append(
            ReductionDecision(
                submission_index=index,
                disposition=disposition,
                reasons=normalized_reasons,
                profile_key=profile_key,
                delegation_id=envelope.delegation_id,
                observation_id=observation.observation_id,
                run_id=envelope.run_id,
                envelope_digest=envelope_digest,
                result_digest=result_digest,
                observation_digest=observation_digest,
            )
        )

    return (
        ProfileSnapshot.from_parts(
            tuple(profiles.values()),
            tuple(delegations.values()),
            tuple(observations.values()),
        ),
        tuple(decisions),
    )


def shadow_reduce(
    start: ProfileSnapshot,
    submissions: Sequence[object],
) -> ShadowReduction:
    """Reduce full sources; duplicates/conflicts become durable decisions."""
    if not isinstance(start, ProfileSnapshot):
        raise ProfileError("start must be a ProfileSnapshot")
    normalized = _normalize_submissions(submissions)
    snapshot, decisions = _reduce_submissions(start, normalized)
    return ShadowReduction(
        snapshot=snapshot,
        start_content_digest=start.content_digest,
        submissions=normalized,
        decisions=decisions,
    )


def _validate_shadow_transition(
    start: ProfileSnapshot, shadow: ShadowReduction
) -> Tuple[ProfileSnapshot, Tuple[ReductionDecision, ...]]:
    if shadow.start_content_digest != start.content_digest:
        raise ProfileError("shadow reduction does not match the frozen start")
    recomputed_snapshot, recomputed_decisions = _reduce_submissions(
        start, shadow.submissions
    )
    if recomputed_decisions != shadow.decisions:
        raise ProfileError(
            "shadow decisions do not match exact source classification"
        )
    if recomputed_snapshot != shadow.snapshot:
        raise ProfileError(
            "shadow snapshot does not match exact source replay"
        )
    return recomputed_snapshot, recomputed_decisions


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
        "corruption": (
            contracts.detached_json_copy(dict(corruption))
            if corruption is not None
            else None
        ),
        "authenticity": "not_established",
        "suffix_completeness": "not_established",
        "limitations": list(ledger.INTEGRITY_LIMITATIONS),
    }


def _snapshot_from_commit(value: Mapping[str, object]) -> ProfileSnapshot:
    return ProfileSnapshot.from_dict(
        {
            "schema_version": value["schema_version"],
            "content_digest": value["state_digest"],
            "profiles": value["profiles"],
            "delegation_bindings": value["delegation_bindings"],
            "observation_bindings": value["observation_bindings"],
        }
    )


def _validate_commit(
    value: object,
    *,
    expected_sequence: int,
    start: ProfileSnapshot,
    expected_previous_digest: Optional[str],
) -> Tuple[Mapping[str, object], ProfileSnapshot]:
    if not isinstance(value, dict) or set(value) != COMMIT_FIELDS:
        raise ProfileError("profile commit fields do not match schema")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != contracts.SCHEMA_VERSION
    ):
        raise ProfileError("unsupported profile commit schema; v2 required")
    if (
        isinstance(value["sequence"], bool)
        or value["sequence"] != expected_sequence
    ):
        raise ProfileError("profile commit sequence is not contiguous")
    contracts.validate_storage_component(value["commit_run_id"], "commit_run_id")
    contracts.validate_timestamp(value["recorded_at"], "recorded_at")
    if value["claimed_terminal_status"] != "verified":
        raise ProfileError(
            "profile commit claimed_terminal_status must be verified"
        )
    contracts.validate_reference(
        value["untrusted_verification_ref"],
        "untrusted_verification_ref",
    )
    if value["start_state_digest"] != start.content_digest:
        raise ProfileError("profile commit start state does not match replay state")
    contracts.validate_digest(value["state_digest"], "state_digest")

    sources = value["source_submissions"]
    decisions = value["decisions"]
    if not isinstance(sources, list) or not isinstance(decisions, list):
        raise ProfileError("profile source submissions/decisions must be arrays")
    submissions = tuple(SourceSubmission.from_dict(item) for item in sources)
    persisted_decisions = tuple(
        ReductionDecision.from_dict(item) for item in decisions
    )
    reduction = shadow_reduce(start, submissions)
    if reduction.decisions != persisted_decisions:
        raise ProfileError(
            "profile commit decisions do not match source replay"
        )
    snapshot = _snapshot_from_commit(value)
    if reduction.snapshot != snapshot:
        raise ProfileError(
            "profile commit snapshot does not match source replay"
        )
    if value["previous_record_digest"] != expected_previous_digest:
        raise ProfileError("profile commit predecessor does not match")
    if expected_previous_digest is not None:
        contracts.validate_digest(
            expected_previous_digest, "previous_record_digest"
        )
    record_digest = contracts.validate_digest(
        value["record_digest"], "record_digest"
    )
    unsigned = dict(value)
    del unsigned["record_digest"]
    if _profile_digest(unsigned) != record_digest:
        raise ProfileError("profile commit record digest does not match")
    return value, snapshot


def _read_commits_unlocked(
    path: Path,
) -> tuple[List[Mapping[str, object]], ProfileSnapshot, Dict[str, object]]:
    snapshot = ProfileSnapshot.empty()
    if not path.exists():
        return [], snapshot, _integrity_report(
            valid=True,
            record_count=0,
            last_record_digest=None,
            state_digest=snapshot.content_digest,
            corruption=None,
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ProfileError("could not read profile log: {}".format(exc)) from exc
    if len(data) > MAX_PROFILE_LOG_BYTES:
        return [], snapshot, _integrity_report(
            valid=False,
            record_count=0,
            last_record_digest=None,
            state_digest=snapshot.content_digest,
            corruption={"line": None, "reason": "profile log exceeds byte bound"},
        )

    commits: List[Mapping[str, object]] = []
    previous_digest: Optional[str] = None
    for line_number, raw_line in enumerate(
        data.splitlines(keepends=True), start=1
    ):
        if line_number > MAX_PROFILE_COMMITS:
            return commits, snapshot, _integrity_report(
                valid=False,
                record_count=len(commits),
                last_record_digest=previous_digest,
                state_digest=snapshot.content_digest,
                corruption={
                    "line": line_number,
                    "reason": "profile log exceeds commit bound",
                },
            )
        if len(raw_line) > MAX_PROFILE_LINE_BYTES:
            return commits, snapshot, _integrity_report(
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
            return commits, snapshot, _integrity_report(
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
            parsed = contracts.strict_json_loads(raw_line[:-1].decode("utf-8"))
            commit, next_snapshot = _validate_commit(
                parsed,
                expected_sequence=line_number,
                start=snapshot,
                expected_previous_digest=previous_digest,
            )
        except (
            UnicodeDecodeError,
            contracts.ContractError,
            ProfileError,
        ) as exc:
            return commits, snapshot, _integrity_report(
                valid=False,
                record_count=len(commits),
                last_record_digest=previous_digest,
                state_digest=snapshot.content_digest,
                corruption={"line": line_number, "reason": str(exc)},
            )
        commits.append(commit)
        snapshot = next_snapshot
        previous_digest = commit["record_digest"]  # type: ignore[assignment]
    return commits, snapshot, _integrity_report(
        valid=True,
        record_count=len(commits),
        last_record_digest=previous_digest,
        state_digest=snapshot.content_digest,
        corruption=None,
    )


class CapabilityProfileStore:
    """Single-writer append store whose snapshots replay from full sources.

    ``claimed_terminal_status`` and ``untrusted_verification_ref`` are in-band
    assertions only. This store does not prove evidence existence, pass status,
    provenance, or verifier independence.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = self.root / "profile-commits.jsonl"
        self.lock_path = self.root / ".profile-commits.lock"

    def verify(self) -> Dict[str, object]:
        with ledger.read_only_file_lock(self.lock_path):
            _, _, report = _read_commits_unlocked(self.path)
        return report

    def current_snapshot(self) -> ProfileSnapshot:
        with ledger.read_only_file_lock(self.lock_path):
            _, snapshot, report = _read_commits_unlocked(self.path)
        if not report["valid"]:
            raise ProfileError(
                "profile log is corrupt: {}".format(report["corruption"])
            )
        return snapshot

    def rebuild_snapshot(self) -> ProfileSnapshot:
        """Replay every retained source contract from an empty state."""
        return self.current_snapshot()

    def read_commits(self) -> List[Mapping[str, object]]:
        with ledger.read_only_file_lock(self.lock_path):
            commits, _, report = _read_commits_unlocked(self.path)
        if not report["valid"]:
            raise ProfileError(
                "profile log is corrupt: {}".format(report["corruption"])
            )
        return commits

    def commit_reduction(
        self,
        *,
        commit_run_id: str,
        start: ProfileSnapshot,
        shadow: ShadowReduction,
        claimed_terminal_status: str,
        untrusted_verification_ref: str,
        recorded_at: Optional[str] = None,
    ) -> Mapping[str, object]:
        contracts.validate_storage_component(commit_run_id, "commit_run_id")
        if claimed_terminal_status != "verified":
            raise ProfileError(
                "profile learning requires claimed_terminal_status exactly verified"
            )
        selected_ref = contracts.validate_reference(
            untrusted_verification_ref, "untrusted_verification_ref"
        )
        selected_time = recorded_at or ledger.utc_now()
        contracts.validate_timestamp(selected_time, "recorded_at")
        if not isinstance(start, ProfileSnapshot):
            raise ProfileError("start must be a ProfileSnapshot")
        if not isinstance(shadow, ShadowReduction):
            raise ProfileError("shadow must be a ShadowReduction")

        self.root.mkdir(parents=True, exist_ok=True)
        with ledger.exclusive_file_lock(self.lock_path):
            commits, current, report = _read_commits_unlocked(self.path)
            if not report["valid"]:
                raise ProfileError(
                    "existing profile log is corrupt: {}".format(
                        report["corruption"]
                    )
                )
            if len(commits) >= MAX_PROFILE_COMMITS:
                raise ProfileError("profile log reached the commit bound")
            if current.content_digest != start.content_digest:
                raise ProfileError(
                    "profile state conflict: current state advanced after run start"
                )
            snapshot, decisions = _validate_shadow_transition(start, shadow)
            if snapshot.content_digest == start.content_digest:
                raise ProfileError("shadow snapshot contains no durable event")

            commit: Dict[str, object] = {
                "schema_version": contracts.SCHEMA_VERSION,
                "sequence": len(commits) + 1,
                "commit_run_id": commit_run_id,
                "recorded_at": selected_time,
                "claimed_terminal_status": claimed_terminal_status,
                "untrusted_verification_ref": selected_ref,
                "start_state_digest": start.content_digest,
                "state_digest": snapshot.content_digest,
                "source_submissions": [
                    item.to_dict() for item in shadow.submissions
                ],
                "decisions": [item.to_dict() for item in decisions],
                "profiles": [item.to_dict() for item in snapshot.profiles],
                "delegation_bindings": [
                    item.to_dict() for item in snapshot.delegation_bindings
                ],
                "observation_bindings": [
                    item.to_dict() for item in snapshot.observation_bindings
                ],
                "previous_record_digest": report["last_record_digest"],
            }
            commit["record_digest"] = _profile_digest(commit)
            raw = _canonical_profile_json(commit).encode("utf-8") + b"\n"
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
        return contracts.strict_json_loads(  # type: ignore[return-value]
            _canonical_profile_json(commit)
        )
