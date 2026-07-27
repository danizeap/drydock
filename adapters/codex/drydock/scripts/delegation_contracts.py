#!/usr/bin/env python3
"""Strict, content-minimal contracts for Drydock delegation evidence.

These values are deliberately non-authoritative. They describe requested work
and observed outcomes; they do not grant permissions or satisfy governance
gates.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
MAX_OBJECTIVE_BYTES = 512 * 1024
MAX_CANONICAL_BYTES = 16 * 1024
MAX_STRING_BYTES = 512
MAX_IDENTIFIER_LENGTH = 128
MAX_REFERENCE_LENGTH = 256
MAX_COLLECTION_ITEMS = 64
MAX_MAPPING_ITEMS = 32
MAX_JSON_DEPTH = 6
MAX_INPUT_DIGESTS = 32
MAX_INTEGER = (1 << 63) - 1
MAX_ATTEMPTS = 100
MAX_DURATION_MS = 7 * 24 * 60 * 60 * 1000
MAX_TOKEN_COUNT = 1_000_000_000
MAX_FINDINGS_PER_OBSERVATION = 1_000_000

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+~-]{0,127}$")
SAFE_STORAGE_COMPONENT = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._+~-]{0,127}$"
)
SAFE_REFERENCE_SEGMENT = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._+~-]{0,127}$"
)
SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {"COM{}".format(number) for number in range(1, 10)}
    | {"LPT{}".format(number) for number in range(1, 10)}
)
SECRET_VALUE = re.compile(
    r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"client[_-]?secret|password)\s*[:=]\s*[\"']?"
    r"[A-Za-z0-9_./+=-]{12,})"
)
_FORBIDDEN_FIELD_ALIASES = frozenset(
    {
        "prompt",
        "system_prompt",
        "user_prompt",
        "objective",
        "task_text",
        "repository_content",
        "repo_content",
        "file_content",
        "raw_response",
        "provider_response",
        "request_body",
        "response_body",
        "credential",
        "credentials",
        "authorization",
        "authorization_header",
        "account_id",
        "api_key",
        "access_token",
        "refresh_token",
        "password",
        "secret",
    }
)
FORBIDDEN_PERSISTED_FIELDS = frozenset(
    re.sub(r"[^a-z0-9]+", "", field.lower())
    for field in _FORBIDDEN_FIELD_ALIASES
)

RESULT_STATUSES = frozenset(
    {
        "completed",
        "failed",
        "timeout",
        "cancelled",
        "invalid_output",
        "unavailable",
    }
)
OBSERVER_KINDS = frozenset({"deterministic_gate", "peer", "verifier", "owner"})
OUTCOMES = frozenset(
    {"accepted", "revision_required", "rejected", "unavailable"}
)
VERIFICATION_STATES = frozenset({"pass", "fail", "not_run", "unavailable"})


class ContractError(ValueError):
    """A persisted delegation value does not satisfy its strict contract."""


def _reject_duplicate_keys(
    pairs: Sequence[Tuple[str, object]],
) -> Dict[str, object]:
    value: Dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("duplicate JSON key: {!r}".format(key))
        value[key] = item
    return value


def strict_json_loads(raw: str) -> object:
    """Load strict JSON, rejecting duplicate keys and non-finite constants."""
    if not isinstance(raw, str):
        raise ContractError("JSON input must be text")
    try:
        return json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ContractError(
                    "non-finite JSON constant: {}".format(token)
                )
            ),
        )
    except ContractError:
        raise
    except (TypeError, ValueError) as exc:
        raise ContractError("invalid JSON: {}".format(exc)) from exc


def canonical_json(value: object) -> str:
    """Return deterministic compact JSON after validating persisted content."""
    validate_json_value(value)
    raw = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(raw.encode("utf-8")) > MAX_CANONICAL_BYTES:
        raise ContractError("canonical JSON exceeds the byte bound")
    return raw


def digest_bytes(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise ContractError("digest input must be bytes")
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    if not isinstance(value, str):
        raise ContractError("digest input must be text")
    return digest_bytes(value.encode("utf-8"))


def digest_json(value: object) -> str:
    return digest_bytes(canonical_json(value).encode("utf-8"))


def _normalized_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _validate_string(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError("{} must be non-empty text".format(field))
    if len(value.encode("utf-8")) > maximum:
        raise ContractError("{} exceeds the byte bound".format(field))
    if "\x00" in value:
        raise ContractError("{} contains NUL".format(field))
    if SECRET_VALUE.search(value):
        raise ContractError("{} matches the persisted secret policy".format(field))
    return value


def validate_identifier(value: object, field: str) -> str:
    text = _validate_string(value, field, MAX_IDENTIFIER_LENGTH)
    if not SAFE_IDENTIFIER.fullmatch(text):
        raise ContractError("{} is not a safe identifier".format(field))
    return text


def validate_storage_component(value: object, field: str) -> str:
    text = _validate_string(value, field, MAX_IDENTIFIER_LENGTH)
    if not SAFE_STORAGE_COMPONENT.fullmatch(text):
        raise ContractError(
            "{} is not a safe storage component".format(field)
        )
    if text.endswith((".", " ")):
        raise ContractError(
            "{} has an unsafe Windows suffix".format(field)
        )
    if text.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        raise ContractError("{} is a reserved Windows name".format(field))
    return text


def validate_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_DIGEST.fullmatch(value):
        raise ContractError("{} must be a sha256 digest".format(field))
    return value


def validate_timestamp(value: object, field: str) -> str:
    text = _validate_string(value, field, 64)
    if not text.endswith("Z"):
        raise ContractError("{} must be UTC and end in Z".format(field))
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("{} is not an ISO-8601 timestamp".format(field)) from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError("{} must be UTC".format(field))
    return text


def validate_reference(value: object, field: str = "reference") -> str:
    text = _validate_string(value, field, MAX_REFERENCE_LENGTH)
    normalized = text.replace("\\", "/")
    if (
        normalized.startswith("/")
        or normalized.startswith("//")
        or WINDOWS_DRIVE.match(normalized)
    ):
        raise ContractError("{} must be relative".format(field))
    path = PurePosixPath(normalized)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError("{} is not a safe relative reference".format(field))
    if path.as_posix() != normalized:
        raise ContractError("{} is not canonical".format(field))
    for part in path.parts:
        if not SAFE_REFERENCE_SEGMENT.fullmatch(part):
            raise ContractError(
                "{} contains an unsafe path segment".format(field)
            )
        if part.endswith((".", " ")):
            raise ContractError(
                "{} has an unsafe Windows suffix".format(field)
            )
        if part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            raise ContractError(
                "{} contains a reserved Windows name".format(field)
            )
    return path.as_posix()


def _validate_nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError("{} must be a non-negative integer".format(field))
    if value > MAX_INTEGER:
        raise ContractError("{} exceeds the integer bound".format(field))
    return value


def _validate_positive_int(value: object, field: str) -> int:
    result = _validate_nonnegative_int(value, field)
    if result == 0:
        raise ContractError("{} must be positive".format(field))
    return result


def _validate_bounded_nonnegative_int(
    value: object, field: str, maximum: int
) -> int:
    result = _validate_nonnegative_int(value, field)
    if result > maximum:
        raise ContractError("{} exceeds the configured bound".format(field))
    return result


def _validate_optional_nonnegative_int(
    value: object, field: str, maximum: int = MAX_INTEGER
) -> Optional[int]:
    if value is None:
        return None
    return _validate_bounded_nonnegative_int(value, field, maximum)


def _validate_enum(value: object, field: str, allowed: Iterable[str]) -> str:
    text = validate_identifier(value, field)
    if text not in allowed:
        raise ContractError("{} has an unsupported value".format(field))
    return text


def _require_exact_fields(
    value: object, expected: Iterable[str], contract: str
) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ContractError("{} must be an object".format(contract))
    expected_set = set(expected)
    actual = set(value)
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        unknown = sorted(actual - expected_set)
        raise ContractError(
            "{} fields do not match the schema; missing={}, unknown={}".format(
                contract, missing, unknown
            )
        )
    return value


def _validate_sequence(
    value: object,
    field: str,
    validator,
    *,
    maximum: int = MAX_COLLECTION_ITEMS,
    unique: bool = False,
) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ContractError("{} must be an array".format(field))
    if len(value) > maximum:
        raise ContractError("{} exceeds the item bound".format(field))
    result = tuple(
        validator(item, "{}[{}]".format(field, index))
        for index, item in enumerate(value)
    )
    if unique and len(set(result)) != len(result):
        raise ContractError("{} contains duplicates".format(field))
    return result


def validate_json_value(value: object, *, _depth: int = 0) -> None:
    """Reject unsafe or unbounded generic metadata before persistence."""
    if _depth > MAX_JSON_DEPTH:
        raise ContractError("persisted JSON exceeds the depth bound")
    if value is None or isinstance(value, bool) or isinstance(value, str):
        if isinstance(value, str):
            _validate_string(value, "persisted string", MAX_STRING_BYTES)
        return
    if isinstance(value, int):
        if abs(value) > MAX_INTEGER:
            raise ContractError("persisted JSON contains an oversized integer")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError("persisted JSON contains a non-finite number")
        return
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ContractError("persisted array exceeds the item bound")
        for item in value:
            validate_json_value(item, _depth=_depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_MAPPING_ITEMS:
            raise ContractError("persisted object exceeds the field bound")
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ContractError("persisted object keys must be non-empty text")
            _validate_string(key, "persisted field", MAX_IDENTIFIER_LENGTH)
            if _normalized_field_name(key) in FORBIDDEN_PERSISTED_FIELDS:
                raise ContractError(
                    "persisted field {!r} is forbidden".format(key)
                )
            validate_json_value(item, _depth=_depth + 1)
        return
    raise ContractError(
        "persisted JSON contains unsupported type {}".format(
            type(value).__name__
        )
    )


@dataclass(frozen=True)
class DelegationEnvelope:
    delegation_id: str
    run_id: str
    task_id: str
    task_class: str
    role: str
    provider: str
    model: str
    reasoning_effort: str
    permission_profile: str
    attempt: int
    max_attempts: int
    objective_digest: str
    input_digests: Tuple[str, ...]
    capacity_snapshot_digest: Optional[str]
    policy_revision: str
    idempotency_key: str
    created_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ContractError("unsupported delegation envelope schema")
        validate_storage_component(self.run_id, "run_id")
        for field in (
            "delegation_id",
            "task_id",
            "task_class",
            "role",
            "provider",
            "model",
            "reasoning_effort",
            "permission_profile",
            "policy_revision",
        ):
            validate_identifier(getattr(self, field), field)
        _validate_positive_int(self.attempt, "attempt")
        _validate_positive_int(self.max_attempts, "max_attempts")
        if self.max_attempts > MAX_ATTEMPTS:
            raise ContractError("max_attempts exceeds the configured bound")
        if self.attempt > self.max_attempts:
            raise ContractError("attempt cannot exceed max_attempts")
        validate_digest(self.objective_digest, "objective_digest")
        normalized_input_digests = _validate_sequence(
            self.input_digests,
            "input_digests",
            validate_digest,
            maximum=MAX_INPUT_DIGESTS,
            unique=True,
        )
        object.__setattr__(self, "input_digests", normalized_input_digests)
        if self.capacity_snapshot_digest is not None:
            validate_digest(
                self.capacity_snapshot_digest, "capacity_snapshot_digest"
            )
        validate_digest(self.idempotency_key, "idempotency_key")
        if self.idempotency_key != digest_json(self._idempotency_seed()):
            raise ContractError(
                "idempotency_key does not match the delegation fields"
            )
        validate_timestamp(self.created_at, "created_at")

    def _idempotency_seed(self) -> Dict[str, object]:
        return {
            "attempt": self.attempt,
            "capacity_snapshot_digest": self.capacity_snapshot_digest,
            "delegation_id": self.delegation_id,
            "input_digests": list(self.input_digests),
            "max_attempts": self.max_attempts,
            "model": self.model,
            "objective_digest": self.objective_digest,
            "permission_profile": self.permission_profile,
            "policy_revision": self.policy_revision,
            "provider": self.provider,
            "reasoning_effort": self.reasoning_effort,
            "role": self.role,
            "run_id": self.run_id,
            "task_class": self.task_class,
            "task_id": self.task_id,
        }

    @classmethod
    def create(
        cls,
        *,
        delegation_id: str,
        run_id: str,
        task_id: str,
        task_class: str,
        role: str,
        provider: str,
        model: str,
        reasoning_effort: str,
        permission_profile: str,
        attempt: int,
        max_attempts: int,
        objective: str,
        input_digests: Sequence[str],
        capacity_snapshot_digest: Optional[str],
        policy_revision: str,
        created_at: str,
    ) -> "DelegationEnvelope":
        if not isinstance(objective, str) or not objective.strip():
            raise ContractError("objective must be non-empty text")
        if len(objective.encode("utf-8")) > MAX_OBJECTIVE_BYTES:
            raise ContractError("objective exceeds the transient input bound")
        objective_digest = digest_text(objective)
        seed = {
            "attempt": attempt,
            "capacity_snapshot_digest": capacity_snapshot_digest,
            "delegation_id": delegation_id,
            "input_digests": list(input_digests),
            "max_attempts": max_attempts,
            "model": model,
            "objective_digest": objective_digest,
            "permission_profile": permission_profile,
            "policy_revision": policy_revision,
            "provider": provider,
            "reasoning_effort": reasoning_effort,
            "role": role,
            "run_id": run_id,
            "task_class": task_class,
            "task_id": task_id,
        }
        return cls(
            delegation_id=delegation_id,
            run_id=run_id,
            task_id=task_id,
            task_class=task_class,
            role=role,
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
            permission_profile=permission_profile,
            attempt=attempt,
            max_attempts=max_attempts,
            objective_digest=objective_digest,
            input_digests=tuple(input_digests),
            capacity_snapshot_digest=capacity_snapshot_digest,
            policy_revision=policy_revision,
            idempotency_key=digest_json(seed),
            created_at=created_at,
        )

    def to_dict(self) -> Dict[str, object]:
        value: Dict[str, object] = {
            "schema_version": self.schema_version,
            "delegation_id": self.delegation_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "task_class": self.task_class,
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "permission_profile": self.permission_profile,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "objective_digest": self.objective_digest,
            "input_digests": list(self.input_digests),
            "capacity_snapshot_digest": self.capacity_snapshot_digest,
            "policy_revision": self.policy_revision,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
        }
        validate_json_value(value)
        return value

    @classmethod
    def from_dict(cls, value: object) -> "DelegationEnvelope":
        fields = (
            "schema_version",
            "delegation_id",
            "run_id",
            "task_id",
            "task_class",
            "role",
            "provider",
            "model",
            "reasoning_effort",
            "permission_profile",
            "attempt",
            "max_attempts",
            "objective_digest",
            "input_digests",
            "capacity_snapshot_digest",
            "policy_revision",
            "idempotency_key",
            "created_at",
        )
        raw = _require_exact_fields(value, fields, "DelegationEnvelope")
        return cls(
            schema_version=raw["schema_version"],  # type: ignore[arg-type]
            delegation_id=raw["delegation_id"],  # type: ignore[arg-type]
            run_id=raw["run_id"],  # type: ignore[arg-type]
            task_id=raw["task_id"],  # type: ignore[arg-type]
            task_class=raw["task_class"],  # type: ignore[arg-type]
            role=raw["role"],  # type: ignore[arg-type]
            provider=raw["provider"],  # type: ignore[arg-type]
            model=raw["model"],  # type: ignore[arg-type]
            reasoning_effort=raw["reasoning_effort"],  # type: ignore[arg-type]
            permission_profile=raw["permission_profile"],  # type: ignore[arg-type]
            attempt=raw["attempt"],  # type: ignore[arg-type]
            max_attempts=raw["max_attempts"],  # type: ignore[arg-type]
            objective_digest=raw["objective_digest"],  # type: ignore[arg-type]
            input_digests=_validate_sequence(
                raw["input_digests"],
                "input_digests",
                validate_digest,
                maximum=MAX_INPUT_DIGESTS,
                unique=True,
            ),
            capacity_snapshot_digest=raw["capacity_snapshot_digest"],  # type: ignore[arg-type]
            policy_revision=raw["policy_revision"],  # type: ignore[arg-type]
            idempotency_key=raw["idempotency_key"],  # type: ignore[arg-type]
            created_at=raw["created_at"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class DelegationResult:
    delegation_id: str
    status: str
    duration_ms: int
    input_tokens: Optional[int]
    cached_input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    artifact_refs: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    error_code: Optional[str]
    error_summary: Optional[str]
    completed_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ContractError("unsupported delegation result schema")
        validate_identifier(self.delegation_id, "delegation_id")
        _validate_enum(self.status, "status", RESULT_STATUSES)
        _validate_bounded_nonnegative_int(
            self.duration_ms, "duration_ms", MAX_DURATION_MS
        )
        for field in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            _validate_optional_nonnegative_int(
                getattr(self, field), field, MAX_TOKEN_COUNT
            )
        if (
            self.cached_input_tokens is not None
            and self.input_tokens is not None
            and self.cached_input_tokens > self.input_tokens
        ):
            raise ContractError("cached_input_tokens cannot exceed input_tokens")
        if self.input_tokens is None or self.output_tokens is None:
            if self.total_tokens is not None:
                raise ContractError(
                    "total_tokens must remain unavailable for partial usage"
                )
        else:
            expected_total = self.input_tokens + self.output_tokens
            if self.total_tokens != expected_total:
                raise ContractError("total_tokens does not match input plus output")
        normalized_artifact_refs = _validate_sequence(
            self.artifact_refs,
            "artifact_refs",
            validate_reference,
            unique=True,
        )
        normalized_evidence_refs = _validate_sequence(
            self.evidence_refs,
            "evidence_refs",
            validate_reference,
            unique=True,
        )
        object.__setattr__(self, "artifact_refs", normalized_artifact_refs)
        object.__setattr__(self, "evidence_refs", normalized_evidence_refs)
        if self.error_code is not None:
            if (
                not isinstance(self.error_code, str)
                or not SAFE_ERROR_CODE.fullmatch(self.error_code)
            ):
                raise ContractError("error_code is invalid")
        if self.error_summary is not None:
            _validate_string(
                self.error_summary, "error_summary", MAX_STRING_BYTES
            )
        if self.status == "completed" and (
            self.error_code is not None or self.error_summary is not None
        ):
            raise ContractError("completed results cannot carry an error")
        validate_timestamp(self.completed_at, "completed_at")

    def to_dict(self) -> Dict[str, object]:
        value: Dict[str, object] = {
            "schema_version": self.schema_version,
            "delegation_id": self.delegation_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "usage": {
                "input_tokens": self.input_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
            },
            "artifact_refs": list(self.artifact_refs),
            "evidence_refs": list(self.evidence_refs),
            "error_code": self.error_code,
            "error_summary": self.error_summary,
            "completed_at": self.completed_at,
        }
        validate_json_value(value)
        return value

    @classmethod
    def from_dict(cls, value: object) -> "DelegationResult":
        fields = (
            "schema_version",
            "delegation_id",
            "status",
            "duration_ms",
            "usage",
            "artifact_refs",
            "evidence_refs",
            "error_code",
            "error_summary",
            "completed_at",
        )
        raw = _require_exact_fields(value, fields, "DelegationResult")
        usage = _require_exact_fields(
            raw["usage"],
            (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "total_tokens",
            ),
            "DelegationResult.usage",
        )
        return cls(
            schema_version=raw["schema_version"],  # type: ignore[arg-type]
            delegation_id=raw["delegation_id"],  # type: ignore[arg-type]
            status=raw["status"],  # type: ignore[arg-type]
            duration_ms=raw["duration_ms"],  # type: ignore[arg-type]
            input_tokens=usage["input_tokens"],  # type: ignore[arg-type]
            cached_input_tokens=usage["cached_input_tokens"],  # type: ignore[arg-type]
            output_tokens=usage["output_tokens"],  # type: ignore[arg-type]
            total_tokens=usage["total_tokens"],  # type: ignore[arg-type]
            artifact_refs=_validate_sequence(
                raw["artifact_refs"],
                "artifact_refs",
                validate_reference,
                unique=True,
            ),
            evidence_refs=_validate_sequence(
                raw["evidence_refs"],
                "evidence_refs",
                validate_reference,
                unique=True,
            ),
            error_code=raw["error_code"],  # type: ignore[arg-type]
            error_summary=raw["error_summary"],  # type: ignore[arg-type]
            completed_at=raw["completed_at"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class OutcomeObservation:
    observation_id: str
    delegation_id: str
    observer_kind: str
    outcome: str
    verification: str
    peer_findings_count: int
    blocking_findings_count: int
    regression_count: int
    evidence_refs: Tuple[str, ...]
    observed_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ContractError("unsupported outcome observation schema")
        validate_identifier(self.observation_id, "observation_id")
        validate_identifier(self.delegation_id, "delegation_id")
        _validate_enum(self.observer_kind, "observer_kind", OBSERVER_KINDS)
        _validate_enum(self.outcome, "outcome", OUTCOMES)
        _validate_enum(
            self.verification, "verification", VERIFICATION_STATES
        )
        _validate_bounded_nonnegative_int(
            self.peer_findings_count,
            "peer_findings_count",
            MAX_FINDINGS_PER_OBSERVATION,
        )
        _validate_bounded_nonnegative_int(
            self.blocking_findings_count,
            "blocking_findings_count",
            MAX_FINDINGS_PER_OBSERVATION,
        )
        _validate_bounded_nonnegative_int(
            self.regression_count,
            "regression_count",
            MAX_FINDINGS_PER_OBSERVATION,
        )
        normalized_evidence_refs = _validate_sequence(
            self.evidence_refs,
            "evidence_refs",
            validate_reference,
            unique=True,
        )
        object.__setattr__(self, "evidence_refs", normalized_evidence_refs)
        validate_timestamp(self.observed_at, "observed_at")

    def to_dict(self) -> Dict[str, object]:
        value: Dict[str, object] = {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "delegation_id": self.delegation_id,
            "observer_kind": self.observer_kind,
            "outcome": self.outcome,
            "verification": self.verification,
            "peer_findings_count": self.peer_findings_count,
            "blocking_findings_count": self.blocking_findings_count,
            "regression_count": self.regression_count,
            "evidence_refs": list(self.evidence_refs),
            "observed_at": self.observed_at,
        }
        validate_json_value(value)
        return value

    @classmethod
    def from_dict(cls, value: object) -> "OutcomeObservation":
        fields = (
            "schema_version",
            "observation_id",
            "delegation_id",
            "observer_kind",
            "outcome",
            "verification",
            "peer_findings_count",
            "blocking_findings_count",
            "regression_count",
            "evidence_refs",
            "observed_at",
        )
        raw = _require_exact_fields(value, fields, "OutcomeObservation")
        return cls(
            schema_version=raw["schema_version"],  # type: ignore[arg-type]
            observation_id=raw["observation_id"],  # type: ignore[arg-type]
            delegation_id=raw["delegation_id"],  # type: ignore[arg-type]
            observer_kind=raw["observer_kind"],  # type: ignore[arg-type]
            outcome=raw["outcome"],  # type: ignore[arg-type]
            verification=raw["verification"],  # type: ignore[arg-type]
            peer_findings_count=raw["peer_findings_count"],  # type: ignore[arg-type]
            blocking_findings_count=raw["blocking_findings_count"],  # type: ignore[arg-type]
            regression_count=raw["regression_count"],  # type: ignore[arg-type]
            evidence_refs=_validate_sequence(
                raw["evidence_refs"],
                "evidence_refs",
                validate_reference,
                unique=True,
            ),
            observed_at=raw["observed_at"],  # type: ignore[arg-type]
        )


PROFILE_COUNT_FIELDS = (
    "sample_count",
    "completed_count",
    "failed_count",
    "timeout_count",
    "cancelled_count",
    "invalid_output_count",
    "unavailable_count",
    "observation_count",
    "accepted_count",
    "revision_required_count",
    "rejected_count",
    "observation_unavailable_count",
    "verification_pass_count",
    "verification_fail_count",
    "verification_not_run_count",
    "verification_unavailable_count",
    "peer_findings_count",
    "blocking_findings_count",
    "regression_count",
    "token_sample_count",
    "total_tokens",
    "duration_sample_count",
    "total_duration_ms",
)


@dataclass(frozen=True)
class CapabilityProfile:
    provider: str
    model: str
    role: str
    task_class: str
    sample_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    timeout_count: int = 0
    cancelled_count: int = 0
    invalid_output_count: int = 0
    unavailable_count: int = 0
    observation_count: int = 0
    accepted_count: int = 0
    revision_required_count: int = 0
    rejected_count: int = 0
    observation_unavailable_count: int = 0
    verification_pass_count: int = 0
    verification_fail_count: int = 0
    verification_not_run_count: int = 0
    verification_unavailable_count: int = 0
    peer_findings_count: int = 0
    blocking_findings_count: int = 0
    regression_count: int = 0
    token_sample_count: int = 0
    total_tokens: int = 0
    duration_sample_count: int = 0
    total_duration_ms: int = 0
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ContractError("unsupported capability profile schema")
        for field in ("provider", "model", "role", "task_class"):
            validate_identifier(getattr(self, field), field)
        for field in PROFILE_COUNT_FIELDS:
            _validate_nonnegative_int(getattr(self, field), field)
        if self.sample_count != sum(
            (
                self.completed_count,
                self.failed_count,
                self.timeout_count,
                self.cancelled_count,
                self.invalid_output_count,
                self.unavailable_count,
            )
        ):
            raise ContractError("result status counts do not equal sample_count")
        if self.observation_count != sum(
            (
                self.accepted_count,
                self.revision_required_count,
                self.rejected_count,
                self.observation_unavailable_count,
            )
        ):
            raise ContractError(
                "outcome counts do not equal observation_count"
            )
        if self.observation_count != sum(
            (
                self.verification_pass_count,
                self.verification_fail_count,
                self.verification_not_run_count,
                self.verification_unavailable_count,
            )
        ):
            raise ContractError(
                "verification counts do not equal observation_count"
            )
        if self.observation_count != self.sample_count:
            raise ContractError(
                "every learned sample must have one outcome observation"
            )
        if self.token_sample_count > self.sample_count:
            raise ContractError("token_sample_count exceeds sample_count")
        if self.duration_sample_count != self.sample_count:
            raise ContractError(
                "duration_sample_count must equal sample_count"
            )

    @property
    def key(self) -> str:
        return "|".join((self.provider, self.model, self.role, self.task_class))

    def to_dict(self) -> Dict[str, object]:
        value: Dict[str, object] = {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "model": self.model,
            "role": self.role,
            "task_class": self.task_class,
        }
        value.update({field: getattr(self, field) for field in PROFILE_COUNT_FIELDS})
        validate_json_value(value)
        return value

    @classmethod
    def from_dict(cls, value: object) -> "CapabilityProfile":
        fields = (
            "schema_version",
            "provider",
            "model",
            "role",
            "task_class",
        ) + PROFILE_COUNT_FIELDS
        raw = _require_exact_fields(value, fields, "CapabilityProfile")
        kwargs = {field: raw[field] for field in fields}
        return cls(**kwargs)  # type: ignore[arg-type]
