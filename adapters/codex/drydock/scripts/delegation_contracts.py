#!/usr/bin/env python3
"""Strict schema-v2 contracts for bounded Drydock delegation evidence.

The root JSON value is depth zero and at most ``MAX_JSON_DEPTH``
parent-to-child edges are accepted. These values are advisory evidence only;
they do not grant permissions or satisfy governance gates.
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


SCHEMA_VERSION = 2
MAX_OBJECTIVE_BYTES = 512 * 1024
MAX_CANONICAL_BYTES = 16 * 1024
MAX_STRING_BYTES = 512
MAX_IDENTIFIER_LENGTH = 128
MAX_REFERENCE_LENGTH = 256
MAX_COLLECTION_ITEMS = 64
MAX_MAPPING_ITEMS = 64
# The root is depth zero. A scalar/container reached through eight edges is valid.
MAX_JSON_DEPTH = 8
MAX_JSON_INTEGER_DIGITS = 19
MAX_INPUT_DIGESTS = 32
MAX_INTEGER = (1 << 63) - 1
MAX_ATTEMPTS = 100
MAX_DURATION_MS = 7 * 24 * 60 * 60 * 1000
MAX_TOKEN_COUNT = 1_000_000_000
MAX_COST_MICROUSD = 1_000_000_000_000
MAX_FINDINGS_PER_OBSERVATION = 1_000_000

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+~-]{0,127}$")
SAFE_STORAGE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+~-]{0,127}$")
SAFE_REFERENCE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+~-]{0,127}$")
SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC_MILLISECOND_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
)
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

RESULT_STATUSES = (
    "completed",
    "failed",
    "timeout",
    "cancelled",
    "invalid_output",
    "unavailable",
)
OBSERVER_KINDS = frozenset({"deterministic_gate", "peer", "verifier", "owner"})
OUTCOMES = ("accepted", "revision_required", "rejected", "unavailable")
VERIFICATION_STATES = ("pass", "fail", "not_run", "unavailable")
USAGE_BASES = ("provider_reported", "provider_estimated", "unavailable")
REASONING_TOKEN_SEMANTICS = (
    "included_in_output",
    "excluded_from_output",
    "unavailable",
)
COST_BASES = ("provider_reported", "provider_estimated", "unavailable")
CONFLICT_REASONS = (
    "duplicate_observation_id",
    "delegation_id_conflict",
    "run_id_conflict",
    "envelope_digest_conflict",
    "result_digest_conflict",
    "observation_content_conflict",
)


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


def _parse_json_constant(token: str) -> object:
    raise ContractError("non-finite JSON constant: {}".format(token))


def _parse_json_int(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > MAX_JSON_INTEGER_DIGITS:
        raise ContractError("JSON integer exceeds the digit bound")
    try:
        value = int(token, 10)
    except ValueError as exc:
        raise ContractError("invalid JSON integer") from exc
    if abs(value) > MAX_INTEGER:
        raise ContractError("JSON integer exceeds the magnitude bound")
    return value


def _parse_json_float(token: str) -> float:
    try:
        value = float(token)
    except ValueError as exc:
        raise ContractError("invalid JSON number") from exc
    if not math.isfinite(value):
        raise ContractError("non-finite JSON number: {}".format(token))
    return value


def strict_json_loads(raw: str) -> object:
    """Load bounded JSON with deterministic duplicate/number/depth behavior."""
    if not isinstance(raw, str):
        raise ContractError("JSON input must be text")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_parse_json_constant,
            parse_float=_parse_json_float,
            parse_int=_parse_json_int,
        )
        validate_json_structure(value)
        return value
    except ContractError:
        raise
    except RecursionError as exc:
        raise ContractError(
            "invalid JSON: nesting exceeds the parser/depth bound"
        ) from exc
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("invalid JSON: {}".format(exc)) from exc


def canonical_json(value: object) -> str:
    """Return deterministic compact JSON after validating persisted content."""
    validate_json_value(value)
    try:
        raw = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except RecursionError as exc:
        raise ContractError(
            "canonical JSON exceeds the parser/depth bound"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ContractError("value is not canonical JSON: {}".format(exc)) from exc
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


def contract_digest(value: object) -> str:
    if not hasattr(value, "to_dict"):
        raise ContractError("contract digest input must expose to_dict")
    return digest_json(value.to_dict())  # type: ignore[attr-defined,no-any-return]


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
        raise ContractError("{} is not a safe storage component".format(field))
    if text.endswith((".", " ")):
        raise ContractError("{} has an unsafe Windows suffix".format(field))
    if text.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        raise ContractError("{} is a reserved Windows name".format(field))
    return text


def validate_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_DIGEST.fullmatch(value):
        raise ContractError("{} must be a sha256 digest".format(field))
    return value


def validate_timestamp(value: object, field: str) -> str:
    text = _validate_string(value, field, 64)
    if not UTC_MILLISECOND_TIMESTAMP.fullmatch(text):
        raise ContractError(
            "{} must match YYYY-MM-DDTHH:MM:SS.mmmZ".format(field)
        )
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise ContractError("{} is not a real UTC timestamp".format(field)) from exc
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
            raise ContractError("{} contains an unsafe path segment".format(field))
        if part.endswith((".", " ")):
            raise ContractError("{} has an unsafe Windows suffix".format(field))
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


def validate_json_structure(value: object, *, _depth: int = 0) -> None:
    """Validate JSON types, finite numbers, integer bounds, and nesting only."""
    if _depth > MAX_JSON_DEPTH:
        raise ContractError("persisted JSON exceeds the depth bound")
    if value is None or isinstance(value, bool) or isinstance(value, str):
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
        for item in value:
            validate_json_structure(item, _depth=_depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("persisted object keys must be text")
            validate_json_structure(item, _depth=_depth + 1)
        return
    raise ContractError(
        "persisted JSON contains unsupported type {}".format(type(value).__name__)
    )


def validate_json_value(value: object, *, _depth: int = 0) -> None:
    """Validate the stricter generic payload boundary."""
    validate_json_structure(value, _depth=_depth)
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, float):
        return
    if isinstance(value, str):
        _validate_string(value, "persisted string", MAX_STRING_BYTES)
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
            if not key:
                raise ContractError("persisted object keys must be non-empty text")
            _validate_string(key, "persisted field", MAX_IDENTIFIER_LENGTH)
            if _normalized_field_name(key) in FORBIDDEN_PERSISTED_FIELDS:
                raise ContractError(
                    "persisted field {!r} is forbidden".format(key)
                )
            validate_json_value(item, _depth=_depth + 1)
        return
    raise ContractError(
        "persisted JSON contains unsupported type {}".format(type(value).__name__)
    )


def detached_json_copy(value: object) -> object:
    """Validate and recursively copy a caller-owned JSON-compatible value."""
    validate_json_value(value)
    if isinstance(value, dict):
        return {key: detached_json_copy(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [detached_json_copy(item) for item in value]
    return value


@dataclass(frozen=True)
class _FrozenJsonObject:
    items: Tuple[Tuple[str, object], ...]


@dataclass(frozen=True)
class _FrozenJsonArray:
    items: Tuple[object, ...]


def _freeze_json_value(value: object, *, _depth: int = 0) -> object:
    if isinstance(value, (_FrozenJsonObject, _FrozenJsonArray)):
        value = _thaw_json_value(value)
    validate_json_value(value, _depth=_depth)
    if isinstance(value, dict):
        return _FrozenJsonObject(
            tuple(
                (key, _freeze_json_value(item, _depth=_depth + 1))
                for key, item in sorted(value.items())
            )
        )
    if isinstance(value, (list, tuple)):
        return _FrozenJsonArray(
            tuple(
                _freeze_json_value(item, _depth=_depth + 1)
                for item in value
            )
        )
    return value


def _thaw_json_value(value: object) -> object:
    if isinstance(value, _FrozenJsonObject):
        return {
            key: _thaw_json_value(item) for key, item in value.items
        }
    if isinstance(value, _FrozenJsonArray):
        return [_thaw_json_value(item) for item in value.items]
    return value


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
    request_binding_digest: str
    created_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != 2:
            raise ContractError("unsupported delegation envelope schema; v2 required")
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
        normalized = _validate_sequence(
            self.input_digests,
            "input_digests",
            validate_digest,
            maximum=MAX_INPUT_DIGESTS,
            unique=True,
        )
        object.__setattr__(self, "input_digests", normalized)
        if self.capacity_snapshot_digest is not None:
            validate_digest(
                self.capacity_snapshot_digest, "capacity_snapshot_digest"
            )
        validate_digest(self.request_binding_digest, "request_binding_digest")
        if self.request_binding_digest != digest_json(self._request_binding_seed()):
            raise ContractError(
                "request_binding_digest does not match the delegation fields"
            )
        validate_timestamp(self.created_at, "created_at")

    def _request_binding_seed(self) -> Dict[str, object]:
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
            request_binding_digest=digest_json(seed),
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
            "request_binding_digest": self.request_binding_digest,
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
            "request_binding_digest",
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
            request_binding_digest=raw["request_binding_digest"],  # type: ignore[arg-type]
            created_at=raw["created_at"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class DelegationResult:
    delegation_id: str
    run_id: str
    runtime_status: str
    duration_ms: int
    usage_basis: str
    input_tokens: Optional[int]
    cached_input_tokens: Optional[int]
    output_tokens: Optional[int]
    reasoning_tokens: Optional[int]
    reasoning_token_semantics: str
    total_tokens: Optional[int]
    cost_basis: str
    cost_microusd: Optional[int]
    artifact_refs: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    error_code: Optional[str]
    untrusted_claimed_terminal_status: Optional[str]
    untrusted_error_summary: Optional[object]
    completed_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != 2:
            raise ContractError("unsupported delegation result schema; v2 required")
        validate_identifier(self.delegation_id, "delegation_id")
        validate_storage_component(self.run_id, "run_id")
        _validate_enum(self.runtime_status, "runtime_status", RESULT_STATUSES)
        _validate_bounded_nonnegative_int(
            self.duration_ms, "duration_ms", MAX_DURATION_MS
        )
        _validate_enum(self.usage_basis, "usage_basis", USAGE_BASES)
        _validate_enum(
            self.reasoning_token_semantics,
            "reasoning_token_semantics",
            REASONING_TOKEN_SEMANTICS,
        )
        for field in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            _validate_optional_nonnegative_int(
                getattr(self, field), field, MAX_TOKEN_COUNT
            )
        if self.usage_basis == "unavailable":
            if any(
                getattr(self, field) is not None
                for field in (
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "reasoning_tokens",
                    "total_tokens",
                )
            ) or self.reasoning_token_semantics != "unavailable":
                raise ContractError(
                    "unavailable usage basis cannot carry token counts/semantics"
                )
        else:
            if (
                self.cached_input_tokens is not None
                and self.input_tokens is not None
                and self.cached_input_tokens > self.input_tokens
            ):
                raise ContractError(
                    "cached_input_tokens cannot exceed input_tokens"
                )
            if self.reasoning_token_semantics == "unavailable":
                if self.reasoning_tokens is not None:
                    raise ContractError(
                        "unavailable reasoning semantics cannot carry tokens"
                    )
            elif self.reasoning_tokens is None:
                raise ContractError(
                    "explicit reasoning semantics require reasoning_tokens"
                )
            if self.input_tokens is None or self.output_tokens is None:
                if self.total_tokens is not None:
                    raise ContractError(
                        "total_tokens must remain unavailable for partial usage"
                    )
            else:
                expected_total = self.input_tokens + self.output_tokens
                if self.reasoning_token_semantics == "excluded_from_output":
                    expected_total += self.reasoning_tokens or 0
                if self.total_tokens != expected_total:
                    raise ContractError(
                        "total_tokens does not match the declared reasoning semantics"
                    )
        _validate_enum(self.cost_basis, "cost_basis", COST_BASES)
        _validate_optional_nonnegative_int(
            self.cost_microusd, "cost_microusd", MAX_COST_MICROUSD
        )
        if (self.cost_basis == "unavailable") != (self.cost_microusd is None):
            raise ContractError(
                "cost basis and cost_microusd availability do not match"
            )
        object.__setattr__(
            self,
            "artifact_refs",
            _validate_sequence(
                self.artifact_refs,
                "artifact_refs",
                validate_reference,
                unique=True,
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_sequence(
                self.evidence_refs,
                "evidence_refs",
                validate_reference,
                unique=True,
            ),
        )
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not SAFE_ERROR_CODE.fullmatch(self.error_code)
        ):
            raise ContractError("error_code is invalid")
        if self.untrusted_claimed_terminal_status is not None:
            validate_identifier(
                self.untrusted_claimed_terminal_status,
                "untrusted_claimed_terminal_status",
            )
        if self.untrusted_error_summary is not None:
            object.__setattr__(
                self,
                "untrusted_error_summary",
                # A result is embedded four levels below a profile commit root.
                # This preserves the global eight-edge persisted JSON maximum.
                _freeze_json_value(
                    self.untrusted_error_summary,
                    _depth=4,
                ),
            )
        if self.runtime_status == "completed" and self.error_code is not None:
            raise ContractError("completed runtime results cannot carry error_code")
        validate_timestamp(self.completed_at, "completed_at")

    def to_dict(self) -> Dict[str, object]:
        value: Dict[str, object] = {
            "schema_version": self.schema_version,
            "delegation_id": self.delegation_id,
            "run_id": self.run_id,
            "runtime_status": self.runtime_status,
            "duration_ms": self.duration_ms,
            "usage": {
                "basis": self.usage_basis,
                "input_tokens": self.input_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "output_tokens": self.output_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "reasoning_token_semantics": self.reasoning_token_semantics,
                "total_tokens": self.total_tokens,
            },
            "cost": {
                "basis": self.cost_basis,
                "microusd": self.cost_microusd,
            },
            "artifact_refs": list(self.artifact_refs),
            "evidence_refs": list(self.evidence_refs),
            "error_code": self.error_code,
            "untrusted_claimed_terminal_status": (
                self.untrusted_claimed_terminal_status
            ),
            "untrusted_error_summary": (
                _thaw_json_value(self.untrusted_error_summary)
                if self.untrusted_error_summary is not None
                else None
            ),
            "completed_at": self.completed_at,
        }
        validate_json_value(value)
        return value

    @classmethod
    def from_dict(cls, value: object) -> "DelegationResult":
        raw = _require_exact_fields(
            value,
            (
                "schema_version",
                "delegation_id",
                "run_id",
                "runtime_status",
                "duration_ms",
                "usage",
                "cost",
                "artifact_refs",
                "evidence_refs",
                "error_code",
                "untrusted_claimed_terminal_status",
                "untrusted_error_summary",
                "completed_at",
            ),
            "DelegationResult",
        )
        usage = _require_exact_fields(
            raw["usage"],
            (
                "basis",
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_tokens",
                "reasoning_token_semantics",
                "total_tokens",
            ),
            "DelegationResult.usage",
        )
        cost = _require_exact_fields(
            raw["cost"], ("basis", "microusd"), "DelegationResult.cost"
        )
        return cls(
            schema_version=raw["schema_version"],  # type: ignore[arg-type]
            delegation_id=raw["delegation_id"],  # type: ignore[arg-type]
            run_id=raw["run_id"],  # type: ignore[arg-type]
            runtime_status=raw["runtime_status"],  # type: ignore[arg-type]
            duration_ms=raw["duration_ms"],  # type: ignore[arg-type]
            usage_basis=usage["basis"],  # type: ignore[arg-type]
            input_tokens=usage["input_tokens"],  # type: ignore[arg-type]
            cached_input_tokens=usage["cached_input_tokens"],  # type: ignore[arg-type]
            output_tokens=usage["output_tokens"],  # type: ignore[arg-type]
            reasoning_tokens=usage["reasoning_tokens"],  # type: ignore[arg-type]
            reasoning_token_semantics=usage["reasoning_token_semantics"],  # type: ignore[arg-type]
            total_tokens=usage["total_tokens"],  # type: ignore[arg-type]
            cost_basis=cost["basis"],  # type: ignore[arg-type]
            cost_microusd=cost["microusd"],  # type: ignore[arg-type]
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
            untrusted_claimed_terminal_status=raw[
                "untrusted_claimed_terminal_status"
            ],  # type: ignore[arg-type]
            untrusted_error_summary=raw["untrusted_error_summary"],
            completed_at=raw["completed_at"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class OutcomeObservation:
    observation_id: str
    delegation_id: str
    run_id: str
    envelope_digest: str
    result_digest: str
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
        if isinstance(self.schema_version, bool) or self.schema_version != 2:
            raise ContractError(
                "unsupported outcome observation schema; v2 required"
            )
        validate_identifier(self.observation_id, "observation_id")
        validate_identifier(self.delegation_id, "delegation_id")
        validate_storage_component(self.run_id, "run_id")
        validate_digest(self.envelope_digest, "envelope_digest")
        validate_digest(self.result_digest, "result_digest")
        _validate_enum(self.observer_kind, "observer_kind", OBSERVER_KINDS)
        _validate_enum(self.outcome, "outcome", OUTCOMES)
        _validate_enum(self.verification, "verification", VERIFICATION_STATES)
        for field in (
            "peer_findings_count",
            "blocking_findings_count",
            "regression_count",
        ):
            _validate_bounded_nonnegative_int(
                getattr(self, field), field, MAX_FINDINGS_PER_OBSERVATION
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_sequence(
                self.evidence_refs,
                "evidence_refs",
                validate_reference,
                unique=True,
            ),
        )
        validate_timestamp(self.observed_at, "observed_at")

    def to_dict(self) -> Dict[str, object]:
        value: Dict[str, object] = {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "delegation_id": self.delegation_id,
            "run_id": self.run_id,
            "envelope_digest": self.envelope_digest,
            "result_digest": self.result_digest,
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
            "run_id",
            "envelope_digest",
            "result_digest",
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
            **{
                field: (
                    _validate_sequence(
                        raw[field],
                        field,
                        validate_reference,
                        unique=True,
                    )
                    if field == "evidence_refs"
                    else raw[field]
                )
                for field in fields
            }
        )  # type: ignore[arg-type]


@dataclass(frozen=True)
class StatusDurationAggregate:
    runtime_status: str
    sample_count: int
    total_duration_ms: int

    def __post_init__(self) -> None:
        _validate_enum(self.runtime_status, "runtime_status", RESULT_STATUSES)
        _validate_positive_int(self.sample_count, "duration sample_count")
        _validate_nonnegative_int(self.total_duration_ms, "total_duration_ms")

    @property
    def key(self) -> str:
        return self.runtime_status

    def to_dict(self) -> Dict[str, object]:
        return {
            "runtime_status": self.runtime_status,
            "sample_count": self.sample_count,
            "total_duration_ms": self.total_duration_ms,
        }

    @classmethod
    def from_dict(cls, value: object) -> "StatusDurationAggregate":
        raw = _require_exact_fields(
            value,
            ("runtime_status", "sample_count", "total_duration_ms"),
            "StatusDurationAggregate",
        )
        return cls(**raw)  # type: ignore[arg-type]


@dataclass(frozen=True)
class TokenUsageAggregate:
    runtime_status: str
    usage_basis: str
    reasoning_token_semantics: str
    sample_count: int
    reasoning_token_sample_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_reasoning_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        _validate_enum(self.runtime_status, "runtime_status", RESULT_STATUSES)
        if _validate_enum(self.usage_basis, "usage_basis", USAGE_BASES) == "unavailable":
            raise ContractError("token aggregate cannot use unavailable basis")
        _validate_enum(
            self.reasoning_token_semantics,
            "reasoning_token_semantics",
            REASONING_TOKEN_SEMANTICS,
        )
        if self.reasoning_token_semantics == "unavailable":
            if self.reasoning_token_sample_count != 0 or self.total_reasoning_tokens != 0:
                raise ContractError(
                    "unavailable reasoning aggregate cannot carry reasoning totals"
                )
        elif self.reasoning_token_sample_count != self.sample_count:
            raise ContractError(
                "reasoning token denominator must equal usage sample_count"
            )
        _validate_positive_int(self.sample_count, "usage sample_count")
        for field in (
            "reasoning_token_sample_count",
            "total_input_tokens",
            "total_output_tokens",
            "total_reasoning_tokens",
            "total_tokens",
        ):
            _validate_nonnegative_int(getattr(self, field), field)

    @property
    def key(self) -> str:
        return "|".join(
            (
                self.runtime_status,
                self.usage_basis,
                self.reasoning_token_semantics,
            )
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "runtime_status": self.runtime_status,
            "usage_basis": self.usage_basis,
            "reasoning_token_semantics": self.reasoning_token_semantics,
            "sample_count": self.sample_count,
            "reasoning_token_sample_count": self.reasoning_token_sample_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_reasoning_tokens": self.total_reasoning_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, value: object) -> "TokenUsageAggregate":
        fields = (
            "runtime_status",
            "usage_basis",
            "reasoning_token_semantics",
            "sample_count",
            "reasoning_token_sample_count",
            "total_input_tokens",
            "total_output_tokens",
            "total_reasoning_tokens",
            "total_tokens",
        )
        return cls(**_require_exact_fields(value, fields, "TokenUsageAggregate"))  # type: ignore[arg-type]


@dataclass(frozen=True)
class CostAggregate:
    runtime_status: str
    cost_basis: str
    sample_count: int
    total_cost_microusd: int

    def __post_init__(self) -> None:
        _validate_enum(self.runtime_status, "runtime_status", RESULT_STATUSES)
        if _validate_enum(self.cost_basis, "cost_basis", COST_BASES) == "unavailable":
            raise ContractError("cost aggregate cannot use unavailable basis")
        _validate_positive_int(self.sample_count, "cost sample_count")
        _validate_nonnegative_int(self.total_cost_microusd, "total_cost_microusd")

    @property
    def key(self) -> str:
        return "|".join((self.runtime_status, self.cost_basis))

    def to_dict(self) -> Dict[str, object]:
        return {
            "runtime_status": self.runtime_status,
            "cost_basis": self.cost_basis,
            "sample_count": self.sample_count,
            "total_cost_microusd": self.total_cost_microusd,
        }

    @classmethod
    def from_dict(cls, value: object) -> "CostAggregate":
        raw = _require_exact_fields(
            value,
            (
                "runtime_status",
                "cost_basis",
                "sample_count",
                "total_cost_microusd",
            ),
            "CostAggregate",
        )
        return cls(**raw)  # type: ignore[arg-type]


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
    "duplicate_observation_id_count",
    "delegation_id_conflict_count",
    "run_id_conflict_count",
    "envelope_digest_conflict_count",
    "result_digest_conflict_count",
    "observation_content_conflict_count",
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
    duplicate_observation_id_count: int = 0
    delegation_id_conflict_count: int = 0
    run_id_conflict_count: int = 0
    envelope_digest_conflict_count: int = 0
    result_digest_conflict_count: int = 0
    observation_content_conflict_count: int = 0
    duration_by_status: Tuple[StatusDurationAggregate, ...] = ()
    token_usage_by_status_and_basis: Tuple[TokenUsageAggregate, ...] = ()
    cost_by_status_and_basis: Tuple[CostAggregate, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != 2:
            raise ContractError("unsupported capability profile schema; v2 required")
        for field in ("provider", "model", "role", "task_class"):
            validate_identifier(getattr(self, field), field)
        for field in PROFILE_COUNT_FIELDS:
            _validate_nonnegative_int(getattr(self, field), field)
        status_counts = {
            status: getattr(self, "{}_count".format(status))
            for status in RESULT_STATUSES
        }
        if self.sample_count != sum(status_counts.values()):
            raise ContractError("result status counts do not equal sample_count")
        if self.observation_count != sum(
            (
                self.accepted_count,
                self.revision_required_count,
                self.rejected_count,
                self.observation_unavailable_count,
            )
        ):
            raise ContractError("outcome counts do not equal observation_count")
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
        if self.sample_count > self.observation_count:
            raise ContractError("sample_count cannot exceed observation_count")

        duration = self._normalize_aggregates(
            self.duration_by_status,
            StatusDurationAggregate,
            "duration_by_status",
        )
        usage = self._normalize_aggregates(
            self.token_usage_by_status_and_basis,
            TokenUsageAggregate,
            "token_usage_by_status_and_basis",
        )
        costs = self._normalize_aggregates(
            self.cost_by_status_and_basis,
            CostAggregate,
            "cost_by_status_and_basis",
        )
        object.__setattr__(self, "duration_by_status", duration)
        object.__setattr__(self, "token_usage_by_status_and_basis", usage)
        object.__setattr__(self, "cost_by_status_and_basis", costs)
        duration_counts = {aggregate.runtime_status: aggregate.sample_count for aggregate in duration}
        for status, count in status_counts.items():
            if duration_counts.get(status, 0) != count:
                raise ContractError(
                    "duration denominator does not match {} count".format(status)
                )
        for status in RESULT_STATUSES:
            if sum(
                item.sample_count
                for item in usage
                if item.runtime_status == status
            ) > status_counts[status]:
                raise ContractError(
                    "token usage denominator exceeds {} count".format(status)
                )
            if sum(
                item.sample_count
                for item in costs
                if item.runtime_status == status
            ) > status_counts[status]:
                raise ContractError(
                    "cost denominator exceeds {} count".format(status)
                )

    @staticmethod
    def _normalize_aggregates(
        values: object, expected_type: type, field: str
    ) -> tuple:
        if not isinstance(values, (list, tuple)):
            raise ContractError("{} must be an array".format(field))
        normalized = tuple(values)
        if any(not isinstance(item, expected_type) for item in normalized):
            raise ContractError("{} contains the wrong aggregate type".format(field))
        keys = [item.key for item in normalized]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ContractError("{} keys must be sorted and unique".format(field))
        return normalized

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
        value["duration_by_status"] = [
            item.to_dict() for item in self.duration_by_status
        ]
        value["token_usage_by_status_and_basis"] = [
            item.to_dict() for item in self.token_usage_by_status_and_basis
        ]
        value["cost_by_status_and_basis"] = [
            item.to_dict() for item in self.cost_by_status_and_basis
        ]
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
        ) + PROFILE_COUNT_FIELDS + (
            "duration_by_status",
            "token_usage_by_status_and_basis",
            "cost_by_status_and_basis",
        )
        raw = _require_exact_fields(value, fields, "CapabilityProfile")
        kwargs = {field: raw[field] for field in fields}
        for field, aggregate_type in (
            ("duration_by_status", StatusDurationAggregate),
            ("token_usage_by_status_and_basis", TokenUsageAggregate),
            ("cost_by_status_and_basis", CostAggregate),
        ):
            items = raw[field]
            if not isinstance(items, list):
                raise ContractError("{} must be an array".format(field))
            kwargs[field] = tuple(aggregate_type.from_dict(item) for item in items)
        return cls(**kwargs)  # type: ignore[arg-type]
