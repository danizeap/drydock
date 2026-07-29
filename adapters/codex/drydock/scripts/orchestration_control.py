#!/usr/bin/env python3
"""Deterministic workflow authority, state transitions, and circuit control."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import stat
import time
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from orchestration_evidence import (
    AT_REST_SECRET,
    EvidenceError,
    SecurityReviewStore,
    _atomic_json,
    _canonical_json,
    _exclusive_record_lock,
    _read_json,
    _require_digest,
)


SCHEMA_VERSION = 3
WORKFLOW_PHASES = (
    "preflight",
    "plan_peer",
    "mutation",
    "cross_review",
    "proof",
    "security_review",
    "verification",
    "integration",
    "push",
    "complete",
)
EXECUTOR_PHASES = frozenset(WORKFLOW_PHASES[1:-1])
TERMINAL_STATUSES = frozenset(
    {"complete", "terminal_blocked", "cancelled_by_owner"}
)
WORKFLOW_STATUSES = frozenset({"active", "blocked", *TERMINAL_STATUSES})
ALLOWED_ACTIONS = frozenset(
    {
        "peer",
        "mutate",
        "cross_review",
        "proof",
        "security_review",
        "verify",
        "integrate",
        "commit",
        "push",
    }
)
ACTION_PHASE = {
    "peer": "plan_peer",
    "mutate": "mutation",
    "cross_review": "cross_review",
    "proof": "proof",
    "security_review": "security_review",
    "verify": "verification",
    "integrate": "integration",
    "commit": "integration",
    "push": "push",
}
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_SKILL = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SAFE_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
OBJECTIVE_ID = re.compile(r"^[0-9a-f]{32}$")
MAX_SUMMARY_CHARS = 512
MAX_PLAN_BYTES = 16 * 1024
MAX_SOURCE_PLAN_BYTES = 512 * 1024
MAX_HISTORY = 64
MAX_ADMISSION_HISTORY = 128
MAX_BLOCKERS = 16
ADMISSION_TTL_SECONDS = 300.0
PUSH_EXECUTOR_AVAILABLE = False
WORKFLOW_FEATURE_ENV = "DRYDOCK_ORCHESTRATION_CONTROL_ENABLED"
MAX_WORKFLOW_PAYLOAD_BYTES = 64 * 1024
PAYLOAD_RETENTION_SECONDS = 3_600.0

DEFAULT_PROCEDURAL_FAILURE_LIMIT = 2
DEFAULT_OBJECTIVE_ELAPSED_LIMIT = 1_800.0
DEFAULT_OBJECTIVE_INPUT_LIMIT = 256 * 1024
DEFAULT_OBJECTIVE_PHASE_ENTRY_LIMIT = 16
DEFAULT_OBJECTIVE_PROVIDER_USD_LIMIT = 3.0
MAX_CIRCUIT_RESOLUTIONS = 1
HARD_CIRCUIT_MAXIMA = {
    "elapsed_seconds": 7_200.0,
    "input_bytes": 2 * 1024 * 1024,
    "phase_entries": 64,
    "procedural_failures": 8,
    "provider_usd": 12.0,
}
MECHANISM_PATHS = (
    "orchestration_control.py",
    "orchestrator.py",
    "orchestration_evidence.py",
    "process_runner.py",
)


class ControlError(EvidenceError):
    """A fail-closed workflow-control error."""


def workflow_feature_enabled(
    environment: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environment is None else environment
    value = source.get(WORKFLOW_FEATURE_ENV, "1")
    if value not in {"0", "1"}:
        raise ControlError(
            f"{WORKFLOW_FEATURE_ENV} must be exactly 0 or 1"
        )
    return value == "1"


def _strict_json_loads(value: str) -> object:
    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = item
        return result

    try:
        return json.loads(value, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ControlError(f"workflow input is not strict JSON: {exc}") from exc


def _exact_keys(
    value: object, expected: set[str], label: str
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ControlError(f"{label} fields do not match the schema")
    return value


def _positive_number(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ControlError(f"{label} must be positive and finite")
    return float(value)


def _nonnegative_number(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ControlError(f"{label} must be nonnegative and finite")
    return float(value)


def _positive_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ControlError(f"{label} must be a positive integer")
    return value


def _bounded_text(
    value: object,
    label: str,
    *,
    maximum: int,
    pattern: re.Pattern[str] | None = None,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or "\x00" in value
    ):
        raise ControlError(f"{label} is missing or outside its bound")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ControlError(f"{label} has an invalid format")
    return value


def _require_objective_id(value: object, label: str = "objective ID") -> str:
    return _bounded_text(
        value, label, maximum=32, pattern=OBJECTIVE_ID
    )


def _optional_objective_id(value: object) -> str | None:
    if value is None:
        return None
    return _require_objective_id(value, "predecessor objective ID")


def _canonical_repository(value: object) -> Path:
    raw = _bounded_text(value, "repository root", maximum=4096)
    path = Path(raw)
    if not path.is_absolute():
        raise ControlError("repository root must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ControlError(f"repository root is unavailable: {exc}") from exc
    if not resolved.is_dir() or path != resolved:
        raise ControlError("repository root must be an existing canonical directory")
    return resolved


def _canonical_relative_path(value: object, label: str) -> str:
    raw = _bounded_text(value, label, maximum=1024)
    if "\\" in raw or any(marker in raw for marker in ("*", "?", "[")):
        raise ControlError(f"{label} must be an exact POSIX repository path")
    path = PurePosixPath(raw)
    if path.is_absolute() or raw != path.as_posix():
        raise ControlError(f"{label} must be canonical and repository-relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ControlError(f"{label} escapes or ambiguously names the repository")
    return raw


def _exact_string_list(
    value: object,
    label: str,
    *,
    allowed: frozenset[str] | None = None,
    paths: bool = False,
    sorted_unique: bool = True,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ControlError(f"{label} must be a non-empty list")
    result: list[str] = []
    for index, item in enumerate(value):
        parsed = (
            _canonical_relative_path(item, f"{label}[{index}]")
            if paths
            else _bounded_text(item, f"{label}[{index}]", maximum=128)
        )
        if allowed is not None and parsed not in allowed:
            raise ControlError(f"{label}[{index}] is unsupported")
        result.append(parsed)
    if len(result) != len(set(result)):
        raise ControlError(f"{label} must contain unique values")
    if sorted_unique and result != sorted(result):
        raise ControlError(f"{label} must be sorted")
    return result


def _validate_limits(value: object, label: str) -> dict[str, object]:
    limits = _exact_keys(
        value,
        {
            "elapsed_seconds",
            "input_bytes",
            "peer_rounds",
            "provider_usd",
        },
        label,
    )
    return {
        "elapsed_seconds": _positive_number(
            limits["elapsed_seconds"], f"{label}.elapsed_seconds"
        ),
        "input_bytes": _positive_integer(
            limits["input_bytes"], f"{label}.input_bytes"
        ),
        "peer_rounds": _positive_integer(
            limits["peer_rounds"], f"{label}.peer_rounds"
        ),
        "provider_usd": _positive_number(
            limits["provider_usd"], f"{label}.provider_usd"
        ),
    }


def _validate_circuit_limits(value: object) -> dict[str, object]:
    limits = _exact_keys(
        value,
        {
            "elapsed_seconds",
            "input_bytes",
            "phase_entries",
            "procedural_failures",
            "provider_usd",
        },
        "circuit limits",
    )
    normalized: dict[str, object] = {
        "elapsed_seconds": _positive_number(
            limits["elapsed_seconds"], "circuit_limits.elapsed_seconds"
        ),
        "input_bytes": _positive_integer(
            limits["input_bytes"], "circuit_limits.input_bytes"
        ),
        "phase_entries": _positive_integer(
            limits["phase_entries"], "circuit_limits.phase_entries"
        ),
        "procedural_failures": _positive_integer(
            limits["procedural_failures"],
            "circuit_limits.procedural_failures",
        ),
        "provider_usd": _positive_number(
            limits["provider_usd"], "circuit_limits.provider_usd"
        ),
    }
    exceeded = [
        key
        for key, maximum in HARD_CIRCUIT_MAXIMA.items()
        if float(normalized[key]) > float(maximum)
    ]
    if exceeded:
        raise ControlError(
            f"circuit limits exceed controller safety maxima: {sorted(exceeded)}"
        )
    return normalized


def _validate_push(value: object, actions: Sequence[str]) -> dict[str, str] | None:
    if value is None:
        if "push" in actions:
            raise ControlError("push action requires an exact push destination")
        return None
    push = _exact_keys(value, {"branch", "remote"}, "push destination")
    remote = _bounded_text(
        push["remote"], "push remote", maximum=128, pattern=SAFE_REMOTE
    )
    branch = _bounded_text(
        push["branch"], "push branch", maximum=255, pattern=SAFE_BRANCH
    )
    if (
        "push" not in actions
        or branch.startswith(("-", "/"))
        or branch.endswith(("/", ".", ".lock"))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
    ):
        raise ControlError("push destination is invalid or not authorized")
    return {"branch": branch, "remote": remote}


def validate_authority(
    value: object,
    *,
    expected_task_id: str,
    now: float | None = None,
) -> dict[str, object]:
    authority = _exact_keys(
        value,
        {
            "allowed_actions",
            "allowed_paths",
            "circuit_limits",
            "expires_at",
            "issued_at",
            "limits",
            "objective_digest",
            "objective_id",
            "owner_action_digest",
            "predecessor_objective_id",
            "push",
            "repository_root",
            "schema_version",
            "task_id",
        },
        "authority manifest",
    )
    if authority["schema_version"] != SCHEMA_VERSION:
        raise ControlError("authority manifest schema version is unsupported")
    objective = _require_digest(
        authority["objective_digest"], "objective digest"  # type: ignore[arg-type]
    )
    objective_id = _require_objective_id(authority["objective_id"])
    predecessor = _optional_objective_id(authority["predecessor_objective_id"])
    if predecessor == objective_id:
        raise ControlError("objective cannot name itself as predecessor")
    owner_action = _require_digest(
        authority["owner_action_digest"],  # type: ignore[arg-type]
        "Owner action digest",
    )
    task_id = _bounded_text(
        authority["task_id"],
        "task ID",
        maximum=128,
        pattern=SAFE_IDENTIFIER,
    )
    if task_id != expected_task_id:
        raise ControlError("authority task ID does not match the current task")
    repository = _canonical_repository(authority["repository_root"])
    paths = _exact_string_list(
        authority["allowed_paths"], "allowed paths", paths=True
    )
    actions = _exact_string_list(
        authority["allowed_actions"],
        "allowed actions",
        allowed=ALLOWED_ACTIONS,
    )
    limits = _validate_limits(authority["limits"], "authority limits")
    circuit_limits = _validate_circuit_limits(authority["circuit_limits"])
    push = _validate_push(authority["push"], actions)
    issued_at = _positive_number(authority["issued_at"], "issued_at")
    expires_at = _positive_number(authority["expires_at"], "expires_at")
    clock = time.time() if now is None else now
    if expires_at <= issued_at or clock < issued_at - 120 or clock >= expires_at:
        raise ControlError("authority manifest is expired or not currently valid")
    return {
        "allowed_actions": actions,
        "allowed_paths": paths,
        "circuit_limits": circuit_limits,
        "expires_at": expires_at,
        "issued_at": issued_at,
        "limits": limits,
        "objective_digest": objective,
        "objective_id": objective_id,
        "owner_action_digest": owner_action,
        "predecessor_objective_id": predecessor,
        "push": push,
        "repository_root": str(repository),
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
    }


def validate_plan(value: object) -> dict[str, object]:
    plan = _exact_keys(
        value,
        {
            "mode",
            "objective_digest",
            "objective_id",
            "phases",
            "primary_skill",
            "push",
            "required_actions",
            "required_paths",
            "resource_request",
            "revision",
            "schema_version",
            "source_plan_path",
            "source_plan_sha256",
            "summary",
            "supersedes",
        },
        "technical plan",
    )
    if plan["schema_version"] != SCHEMA_VERSION:
        raise ControlError("technical plan schema version is unsupported")
    objective = _require_digest(
        plan["objective_digest"], "objective digest"  # type: ignore[arg-type]
    )
    objective_id = _require_objective_id(plan["objective_id"])
    revision = _positive_integer(plan["revision"], "plan revision")
    supersedes = plan["supersedes"]
    if revision == 1:
        if supersedes is not None:
            raise ControlError("plan revision one must not supersede another plan")
    else:
        if not isinstance(supersedes, str):
            raise ControlError("later plan revisions require a predecessor digest")
        _require_digest(supersedes, "superseded plan digest")
    summary = _bounded_text(
        plan["summary"], "plan summary", maximum=MAX_SUMMARY_CHARS
    )
    if "\n" in summary or AT_REST_SECRET.search(summary):
        raise ControlError("plan summary is multiline or matches the secret policy")
    mode = _bounded_text(plan["mode"], "plan mode", maximum=8)
    if mode not in {"LITE", "STANDARD", "FULL"}:
        raise ControlError("plan mode is unsupported")
    primary_skill = _bounded_text(
        plan["primary_skill"],
        "primary skill",
        maximum=64,
        pattern=SAFE_SKILL,
    )
    paths = _exact_string_list(
        plan["required_paths"], "required paths", paths=True
    )
    actions = _exact_string_list(
        plan["required_actions"],
        "required actions",
        allowed=ALLOWED_ACTIONS,
    )
    phases = _exact_string_list(
        plan["phases"],
        "phases",
        allowed=frozenset(WORKFLOW_PHASES),
        sorted_unique=False,
    )
    phase_indexes = [WORKFLOW_PHASES.index(phase) for phase in phases]
    if (
        phases[0] != "preflight"
        or phases[-1] != "complete"
        or phase_indexes != sorted(phase_indexes)
    ):
        raise ControlError(
            "plan phases must be an ordered workflow subsequence from "
            "preflight to complete"
        )
    for action in actions:
        if ACTION_PHASE[action] not in phases:
            raise ControlError(f"plan action {action} lacks its workflow phase")
    if "mutate" in actions:
        required_for_mutation = {"proof", "security_review"}
        missing_actions = sorted(required_for_mutation - set(actions))
        if missing_actions:
            raise ControlError(
                "mutating plan lacks required proof/security actions: "
                f"{missing_actions}"
            )
        if phases.index("proof") > phases.index("security_review"):
            raise ControlError(
                "mutating plan security review must follow exact-candidate proof"
            )
    if ("push" in phases) != ("push" in actions):
        raise ControlError("push phase and push action must agree")
    push = _validate_push(plan["push"], actions)
    resources = _validate_limits(plan["resource_request"], "resource request")
    source_plan_path = _canonical_relative_path(
        plan["source_plan_path"], "source plan path"
    )
    source_plan_sha256 = _require_digest(
        plan["source_plan_sha256"], "source plan SHA-256"  # type: ignore[arg-type]
    )
    if source_plan_path not in paths:
        raise ControlError("source plan path must be a required plan path")
    normalized = {
        "mode": mode,
        "objective_digest": objective,
        "objective_id": objective_id,
        "phases": phases,
        "primary_skill": primary_skill,
        "push": push,
        "required_actions": actions,
        "required_paths": paths,
        "resource_request": resources,
        "revision": revision,
        "schema_version": SCHEMA_VERSION,
        "source_plan_path": source_plan_path,
        "source_plan_sha256": source_plan_sha256,
        "summary": summary,
        "supersedes": supersedes,
    }
    if len(_canonical_json(normalized)) > MAX_PLAN_BYTES:
        raise ControlError("technical plan exceeds its compact byte bound")
    return normalized


def canonical_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def authority_scope_digest(authority: Mapping[str, object]) -> str:
    scope = {
        key: value
        for key, value in authority.items()
        if key not in {"expires_at", "issued_at", "owner_action_digest"}
    }
    return canonical_digest(scope)


def mechanism_digest() -> str:
    root = Path(__file__).resolve(strict=True).parent
    digest = hashlib.sha256(b"drydock orchestration mechanism v2\0")
    for name in MECHANISM_PATHS:
        path = (root / name).resolve(strict=True)
        if path.parent != root or not path.is_file() or path.is_symlink():
            raise ControlError("orchestration mechanism path is not a plain file")
        body = path.read_bytes()
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    return digest.hexdigest()


def _source_plan_digest(
    authority: Mapping[str, object], plan: Mapping[str, object]
) -> str:
    repository = Path(str(authority["repository_root"]))
    candidate = repository / str(plan["source_plan_path"])
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ControlError(f"canonical source plan is unavailable: {exc}") from exc
    if (
        repository not in resolved.parents
        or candidate.is_symlink()
        or not resolved.is_file()
    ):
        raise ControlError("canonical source plan is not a plain repository file")
    body = resolved.read_bytes()
    if len(body) > MAX_SOURCE_PLAN_BYTES:
        raise ControlError("canonical source plan exceeds its byte bound")
    return hashlib.sha256(body).hexdigest()


def _assert_source_plan(
    authority: Mapping[str, object], plan: Mapping[str, object]
) -> None:
    observed = _source_plan_digest(authority, plan)
    if observed != plan["source_plan_sha256"]:
        raise ControlError(
            "structured plan is stale relative to canonical packet plan.md"
        )


def preflight(
    authority_value: object,
    plan_value: object,
    *,
    expected_task_id: str,
    now: float | None = None,
) -> dict[str, object]:
    authority = validate_authority(
        authority_value, expected_task_id=expected_task_id, now=now
    )
    plan = validate_plan(plan_value)
    if (
        plan["objective_digest"] != authority["objective_digest"]
        or plan["objective_id"] != authority["objective_id"]
    ):
        raise ControlError("plan objective is outside Owner authority")
    _assert_source_plan(authority, plan)
    unapproved_paths = sorted(
        set(plan["required_paths"]) - set(authority["allowed_paths"])  # type: ignore[arg-type]
    )
    if unapproved_paths:
        raise ControlError(
            f"plan paths are outside Owner authority: {unapproved_paths}"
        )
    unapproved_actions = sorted(
        set(plan["required_actions"])  # type: ignore[arg-type]
        - set(authority["allowed_actions"])  # type: ignore[arg-type]
    )
    if unapproved_actions:
        raise ControlError(
            f"plan actions are outside Owner authority: {unapproved_actions}"
        )
    plan_limits = plan["resource_request"]
    authority_limits = authority["limits"]
    assert isinstance(plan_limits, dict) and isinstance(authority_limits, dict)
    exceeded = [
        key
        for key in plan_limits
        if float(plan_limits[key]) > float(authority_limits[key])
    ]
    if exceeded:
        raise ControlError(
            f"plan resources exceed Owner authority: {sorted(exceeded)}"
        )
    if "push" in plan["required_actions"]:  # type: ignore[operator]
        if authority["push"] is None or plan["push"] != authority["push"]:
            raise ControlError(
                "plan push destination differs from Owner authority"
            )
    return {
        "authority": authority,
        "authority_digest": canonical_digest(authority),
        "authority_scope_digest": authority_scope_digest(authority),
        "mechanism_digest": mechanism_digest(),
        "plan": plan,
        "plan_digest": canonical_digest(plan),
    }


def stable_blocker_id(text: str) -> str:
    parsed = _bounded_text(text, "blocker", maximum=4096)
    return "B-" + hashlib.sha256(parsed.encode("utf-8")).hexdigest()[:12]


def compact_delta_review(
    *,
    current_plan: Mapping[str, object],
    previous_blockers: Sequence[str],
    changed_fields: Mapping[str, object],
) -> dict[str, object]:
    plan = validate_plan(dict(current_plan))
    if not previous_blockers or len(previous_blockers) > MAX_BLOCKERS:
        raise ControlError("delta review blocker count is outside its bound")
    blockers: list[dict[str, str]] = []
    for blocker in previous_blockers:
        text = _bounded_text(blocker, "blocker", maximum=4096)
        blockers.append({"id": stable_blocker_id(text), "text": text})
    if (
        not isinstance(changed_fields, Mapping)
        or not changed_fields
        or any(
            not isinstance(key, str) or key not in plan
            for key in changed_fields
        )
    ):
        raise ControlError("delta review changed fields are empty or unknown")
    normalized_changes = {
        key: plan[key] for key in sorted(changed_fields)
    }
    payload = {
        "changed_fields": normalized_changes,
        "objective_digest": plan["objective_digest"],
        "objective_id": plan["objective_id"],
        "plan_digest": canonical_digest(plan),
        "plan_revision": plan["revision"],
        "review_kind": "technical_delta",
        "schema_version": SCHEMA_VERSION,
        "unresolved_blockers": blockers,
    }
    if len(_canonical_json(payload)) > MAX_PLAN_BYTES:
        raise ControlError("delta review exceeds its compact byte bound")
    return payload


def _next_phase(plan: Mapping[str, object], current: str) -> str:
    phases = plan["phases"]
    assert isinstance(phases, list)
    index = phases.index(current)
    return phases[index + 1]


def _phase_index(phase: str) -> int:
    return WORKFLOW_PHASES.index(phase)


class OwnerActionLedger:
    """Single-use local action identifiers; identifying, never authenticating."""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True) / "owner-actions"

    def consume(
        self,
        action_digest: str,
        *,
        objective_id: str,
        transition: str,
        binding_digest: str,
        now: float,
    ) -> dict[str, object]:
        digest = _require_digest(action_digest, "Owner action digest")
        objective = _require_objective_id(objective_id)
        binding = _require_digest(binding_digest, "action binding digest")
        transition_name = _bounded_text(
            transition, "action transition", maximum=64, pattern=SAFE_IDENTIFIER
        )
        path = self.root / f"{digest}.json"
        try:
            with _exclusive_record_lock(path):
                if path.exists():
                    raise ControlError(
                        "Owner action digest was already consumed"
                    )
                record = {
                    "action_digest": digest,
                    "binding_digest": binding,
                    "consumed_at": now,
                    "objective_id": objective,
                    "schema_version": SCHEMA_VERSION,
                    "store_authentication": "none_user_writable",
                    "transition": transition_name,
                }
                _atomic_json(path, record)
        except ControlError:
            raise
        except EvidenceError as exc:
            raise ControlError(str(exc)) from exc
        return record


def _empty_circuit(limits: Mapping[str, object]) -> dict[str, object]:
    totals = {
        "elapsed_seconds": 0.0,
        "input_bytes": 0,
        "phase_entries": 0,
        "procedural_failures": 0,
        "provider_usd": 0.0,
        "unknown_provider_cost_entries": 0,
    }
    return {
        "baseline": dict(totals),
        "limits": dict(limits),
        "open": False,
        "opened_at": None,
        "opening_snapshot": None,
        "resolution_count": 0,
        "totals": totals,
        "worker_started": False,
    }


class WorkflowStore:
    """One current plan, action ledger, and circuit for an immutable objective."""

    def __init__(self, root: Path, objective_id: str):
        self.root = root.resolve(strict=True)
        self.objective_id = _require_objective_id(objective_id)
        self.path = self.root / "workflows" / f"{self.objective_id}.json"
        self.plan_root = self.root / "plans"
        self.actions = OwnerActionLedger(self.root)

    def _validate_plan_reference(self, record: Mapping[str, object]) -> None:
        plan = record.get("current_plan")
        digest = record.get("current_plan_digest")
        if not isinstance(plan, dict) or not isinstance(digest, str):
            raise ControlError("workflow current-plan reference is invalid")
        _require_digest(digest, "current plan digest")
        if canonical_digest(plan) != digest:
            raise ControlError("workflow current plan digest is mismatched")
        if validate_plan(plan) != plan:
            raise ControlError("workflow current plan contract is not canonical")
        path = self.plan_root / f"{digest}.json"
        try:
            stored = _read_json(path)
        except EvidenceError as exc:
            raise ControlError(
                f"workflow current plan body is unavailable: {exc}"
            ) from exc
        if stored != plan:
            raise ControlError("workflow current plan body is mismatched")

    def _read(self) -> dict[str, object]:
        record = _read_json(self.path)
        if (
            record.get("schema_version") != SCHEMA_VERSION
            or record.get("objective_id") != self.objective_id
            or record.get("status") not in WORKFLOW_STATUSES
        ):
            raise ControlError("workflow record identity or status is invalid")
        self._validate_plan_reference(record)
        return record

    def read(self) -> dict[str, object]:
        return self._read()

    def _persist_plan(self, plan: Mapping[str, object], digest: str) -> None:
        path = self.plan_root / f"{digest}.json"
        if path.exists():
            if _read_json(path) != dict(plan):
                raise ControlError("stored plan digest maps to different content")
            return
        _atomic_json(path, dict(plan))

    def _transition_binding(
        self,
        transition: str,
        checked: Mapping[str, object],
        *,
        snapshot_digest: str | None = None,
    ) -> str:
        return canonical_digest(
            {
                "authority": checked["authority_digest"],
                "mechanism": checked["mechanism_digest"],
                "objective_id": self.objective_id,
                "plan": checked["plan_digest"],
                "snapshot": snapshot_digest,
                "transition": transition,
            }
        )

    def start(
        self,
        authority_value: object,
        plan_value: object,
        *,
        expected_task_id: str,
        now: float | None = None,
    ) -> dict[str, object]:
        clock = time.time() if now is None else now
        if not workflow_feature_enabled():
            raise ControlError(
                "workflow control feature is disabled; governed execution "
                "fails closed"
            )
        checked = preflight(
            authority_value,
            plan_value,
            expected_task_id=expected_task_id,
            now=clock,
        )
        authority = checked["authority"]
        plan = checked["plan"]
        assert isinstance(authority, dict) and isinstance(plan, dict)
        if authority["objective_id"] != self.objective_id:
            raise ControlError("workflow store objective ID differs from authority")
        if plan["revision"] != 1:
            raise ControlError("a new workflow must begin at plan revision one")
        if self.path.exists():
            existing = self._read()
            if (
                existing["status"] == "active"
                and existing["authority_digest"] == checked["authority_digest"]
                and existing["current_plan_digest"] == checked["plan_digest"]
            ):
                return {**existing, "recovered": True}
            raise ControlError(
                "objective already has workflow history; recover, revise, resume, "
                "or resolve it instead of starting another plan"
            )
        self.actions.consume(
            str(authority["owner_action_digest"]),
            objective_id=self.objective_id,
            transition="create",
            binding_digest=self._transition_binding("create", checked),
            now=clock,
        )
        self._persist_plan(plan, str(checked["plan_digest"]))
        next_phase = _next_phase(plan, "preflight")
        record: dict[str, object] = {
            "admission": None,
            "admission_history": [],
            "authority": authority,
            "authority_digest": checked["authority_digest"],
            "authority_scope_digest": checked["authority_scope_digest"],
            "candidate_digest": None,
            "circuit": _empty_circuit(authority["circuit_limits"]),  # type: ignore[arg-type]
            "completed_phases": [
                {
                    "candidate_digest": None,
                    "evidence_digest": canonical_digest(
                        {
                            "authority": checked["authority_digest"],
                            "authority_scope": checked[
                                "authority_scope_digest"
                            ],
                            "mechanism": checked["mechanism_digest"],
                            "plan": checked["plan_digest"],
                        }
                    ),
                    "phase": "preflight",
                    "recorded_at": clock,
                }
            ],
            "created_at": clock,
            "current_phase": next_phase,
            "current_plan": plan,
            "current_plan_digest": checked["plan_digest"],
            "feature_enabled": True,
            "history": [],
            "mechanism_digest": checked["mechanism_digest"],
            "objective_digest": authority["objective_digest"],
            "objective_id": self.objective_id,
            "predecessor_objective_id": authority[
                "predecessor_objective_id"
            ],
            "resume": None,
            "schema_version": SCHEMA_VERSION,
            "status": "active",
            "task_id": authority["task_id"],
            "updated_at": clock,
        }
        _atomic_json(self.path, record)
        return {**record, "recovered": False}

    def _replace_plan(
        self,
        record: dict[str, object],
        checked: Mapping[str, object],
        *,
        now: float,
    ) -> None:
        current = record["current_plan"]
        plan = checked["plan"]
        assert isinstance(current, dict) and isinstance(plan, dict)
        if plan["revision"] != int(current["revision"]) + 1:
            raise ControlError("plan revision must increment exactly once")
        if plan["supersedes"] != record["current_plan_digest"]:
            raise ControlError("plan does not supersede the exact current digest")
        history = record["history"]
        assert isinstance(history, list)
        if len(history) >= MAX_HISTORY:
            raise ControlError("workflow plan history reached its bound")
        history.append(
            {
                "digest": record["current_plan_digest"],
                "revision": current["revision"],
                "state": "superseded",
                "superseded_at": now,
            }
        )
        self._persist_plan(plan, str(checked["plan_digest"]))
        record["current_plan"] = plan
        record["current_plan_digest"] = checked["plan_digest"]

    def _reset_after_identity_change(
        self,
        record: dict[str, object],
        checked: Mapping[str, object],
        *,
        now: float,
    ) -> None:
        record["mechanism_digest"] = checked["mechanism_digest"]
        record["candidate_digest"] = None
        record["admission"] = None
        record["resume"] = None
        record["status"] = "active"
        record["current_phase"] = _next_phase(
            record["current_plan"], "preflight"  # type: ignore[arg-type]
        )
        record["completed_phases"] = [
            {
                "candidate_digest": None,
                "evidence_digest": canonical_digest(
                    {
                        "authority": checked["authority_digest"],
                        "authority_scope": checked[
                            "authority_scope_digest"
                        ],
                        "mechanism": checked["mechanism_digest"],
                        "plan": checked["plan_digest"],
                    }
                ),
                "phase": "preflight",
                "recorded_at": now,
            }
        ]

    def revise(
        self,
        authority_value: object,
        plan_value: object,
        *,
        expected_task_id: str,
        now: float | None = None,
    ) -> dict[str, object]:
        clock = time.time() if now is None else now
        checked = preflight(
            authority_value,
            plan_value,
            expected_task_id=expected_task_id,
            now=clock,
        )
        authority = checked["authority"]
        assert isinstance(authority, dict)
        if authority["objective_id"] != self.objective_id:
            raise ControlError("workflow store objective ID differs from authority")
        with _exclusive_record_lock(self.path):
            record = self._read()
            if record["circuit"]["open"]:  # type: ignore[index]
                raise ControlError("an open circuit requires explicit resolution")
            if checked["authority_scope_digest"] != record[
                "authority_scope_digest"
            ]:
                raise ControlError(
                    "ordinary plan revision cannot change Owner authority scope"
                )
            self.actions.consume(
                str(authority["owner_action_digest"]),
                objective_id=self.objective_id,
                transition="revise",
                binding_digest=self._transition_binding("revise", checked),
                now=clock,
            )
            self._replace_plan(record, checked, now=clock)
            record["authority"] = authority
            record["authority_digest"] = checked["authority_digest"]
            self._reset_after_identity_change(record, checked, now=clock)
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return record

    def _circuit_delta(
        self, circuit: Mapping[str, object], key: str
    ) -> float:
        totals = circuit["totals"]
        baseline = circuit["baseline"]
        assert isinstance(totals, dict) and isinstance(baseline, dict)
        return float(totals[key]) - float(baseline[key])

    def _circuit_limit_reason(
        self, circuit: Mapping[str, object]
    ) -> str | None:
        limits = circuit["limits"]
        assert isinstance(limits, dict)
        for key in (
            "procedural_failures",
            "phase_entries",
            "input_bytes",
            "elapsed_seconds",
            "provider_usd",
        ):
            if self._circuit_delta(circuit, key) >= float(limits[key]):
                return f"objective_{key}_limit"
        return None

    def _open_circuit(
        self, record: dict[str, object], *, now: float, reason: str
    ) -> None:
        circuit = record["circuit"]
        assert isinstance(circuit, dict)
        circuit["open"] = True
        circuit["opened_at"] = now
        snapshot = {
            "authority_digest": record["authority_digest"],
            "authority_scope_digest": record["authority_scope_digest"],
            "baseline": circuit["baseline"],
            "mechanism_digest": record["mechanism_digest"],
            "plan_digest": record["current_plan_digest"],
            "reason": reason,
            "resolution_count": circuit["resolution_count"],
            "totals": circuit["totals"],
        }
        circuit["opening_snapshot"] = {
            **snapshot,
            "snapshot_digest": canonical_digest(snapshot),
        }
        record["admission"] = None
        if int(circuit["resolution_count"]) >= MAX_CIRCUIT_RESOLUTIONS:
            record["resume"] = None
            record["status"] = "terminal_blocked"
        else:
            record["resume"] = {
                "phase": record["current_phase"],
                "preconditions_digest": canonical_digest(
                    {
                        "candidate": record["candidate_digest"],
                        "phase": record["current_phase"],
                        "plan": record["current_plan_digest"],
                    }
                ),
                "reason": "circuit_open",
            }
            record["status"] = "blocked"

    def admit(
        self,
        phase: str,
        *,
        input_digest: str,
        input_bytes: int,
        candidate_digest: str | None = None,
        now: float | None = None,
    ) -> dict[str, object]:
        if phase not in EXECUTOR_PHASES:
            raise ControlError("phase is not an executable workflow phase")
        if phase == "push" and not PUSH_EXECUTOR_AVAILABLE:
            raise ControlError(
                "workflow push is unavailable until its dedicated wrapper exists"
            )
        _require_digest(input_digest, "phase input digest")
        size = _positive_integer(input_bytes, "phase input bytes")
        candidate = (
            None
            if candidate_digest is None
            else _require_digest(candidate_digest, "candidate digest")
        )
        clock = time.time() if now is None else now
        with _exclusive_record_lock(self.path):
            record = self._read()
            if record["status"] != "active":
                raise ControlError("workflow is not active")
            authority = record["authority"]
            plan = record["current_plan"]
            assert isinstance(authority, dict) and isinstance(plan, dict)
            _assert_source_plan(authority, plan)
            circuit = record["circuit"]
            assert isinstance(circuit, dict)
            if circuit["open"]:
                raise ControlError("objective circuit is open")
            if record["current_phase"] != phase:
                raise ControlError(
                    f"workflow expects {record['current_phase']}, not {phase}"
                )
            if record["admission"] is not None:
                raise ControlError("workflow phase already has a live admission")
            current_candidate = record["candidate_digest"]
            if _phase_index(phase) > _phase_index("mutation"):
                if candidate is None or candidate != current_candidate:
                    raise ControlError(
                        "phase candidate does not match the current candidate"
                    )
            totals = circuit["totals"]
            assert isinstance(totals, dict)
            totals["phase_entries"] = int(totals["phase_entries"]) + 1
            totals["input_bytes"] = int(totals["input_bytes"]) + size
            open_reason = self._circuit_limit_reason(circuit)
            if open_reason is not None:
                self._open_circuit(record, now=clock, reason=open_reason)
                record["updated_at"] = clock
                _atomic_json(self.path, record)
                raise ControlError(
                    f"objective circuit opened before spawn: {open_reason}"
                )
            admission = {
                "admission_id": secrets.token_hex(32),
                "candidate_digest": current_candidate,
                "expires_at": min(
                    clock + ADMISSION_TTL_SECONDS,
                    float(authority["expires_at"]),
                ),
                "input_bytes": size,
                "input_digest": input_digest,
                "issued_at": clock,
                "manifest_digest": record["authority_digest"],
                "mechanism_digest": record["mechanism_digest"],
                "nonce": secrets.token_hex(32),
                "phase": phase,
                "plan_digest": record["current_plan_digest"],
                "prior_gates_digest": canonical_digest(
                    record["completed_phases"]
                ),
                "state": "issued",
                "workflow_id": self.objective_id,
            }
            record["admission"] = admission
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return admission

    def consume_admission(
        self,
        phase: str,
        *,
        admission_id: str,
        input_digest: str,
        candidate_digest: str | None = None,
        now: float | None = None,
    ) -> dict[str, object]:
        _require_digest(input_digest, "phase input digest")
        candidate = (
            None
            if candidate_digest is None
            else _require_digest(candidate_digest, "candidate digest")
        )
        clock = time.time() if now is None else now
        with _exclusive_record_lock(self.path):
            record = self._read()
            admission = record["admission"]
            if (
                record["status"] != "active"
                or not isinstance(admission, dict)
                or admission.get("admission_id") != admission_id
                or admission.get("phase") != phase
                or admission.get("state") != "issued"
                or admission.get("input_digest") != input_digest
                or admission.get("candidate_digest") != candidate
                or admission.get("manifest_digest")
                != record["authority_digest"]
                or admission.get("plan_digest")
                != record["current_plan_digest"]
                or admission.get("mechanism_digest")
                != record["mechanism_digest"]
                or admission.get("prior_gates_digest")
                != canonical_digest(record["completed_phases"])
            ):
                raise ControlError(
                    "executor admission is missing, stale, consumed, or mismatched"
                )
            expires_at = admission.get("expires_at")
            if (
                not isinstance(expires_at, (int, float))
                or isinstance(expires_at, bool)
                or clock >= float(expires_at)
            ):
                admission["state"] = "expired"
                admission["consumed_at"] = clock
                record["status"] = "blocked"
                record["resume"] = {
                    "phase": phase,
                    "preconditions_digest": canonical_digest(
                        {
                            "candidate": record["candidate_digest"],
                            "phase": phase,
                            "plan": record["current_plan_digest"],
                        }
                    ),
                    "reason": "admission_expired",
                }
                record["updated_at"] = clock
                _atomic_json(self.path, record)
                raise ControlError("executor admission expired before spawn")
            admission["state"] = "consumed"
            admission["consumed_at"] = clock
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return dict(admission)

    def _archive_admission(
        self, record: dict[str, object], *, finished_at: float
    ) -> None:
        admission = record["admission"]
        if isinstance(admission, dict):
            archived = {**admission, "finished_at": finished_at}
            history = record["admission_history"]
            assert isinstance(history, list)
            history.append(archived)
            if len(history) > MAX_ADMISSION_HISTORY:
                del history[: len(history) - MAX_ADMISSION_HISTORY]
        record["admission"] = None

    def recover_expired_admission(
        self, *, now: float | None = None
    ) -> dict[str, object]:
        """Burn a consumed, expired admission after a crashed executor."""
        clock = time.time() if now is None else now
        with _exclusive_record_lock(self.path):
            record = self._read()
            admission = record["admission"]
            if (
                record["status"] != "active"
                or not isinstance(admission, dict)
                or admission.get("state") != "consumed"
            ):
                raise ControlError(
                    "workflow has no consumed admission to recover"
                )
            expires_at = admission.get("expires_at")
            consumed_at = admission.get("consumed_at")
            if (
                not isinstance(expires_at, (int, float))
                or isinstance(expires_at, bool)
                or not isinstance(consumed_at, (int, float))
                or isinstance(consumed_at, bool)
                or clock < float(expires_at)
            ):
                raise ControlError(
                    "consumed admission is not yet expired"
                )
            admission["state"] = "burned_after_executor_crash"
            circuit = record["circuit"]
            totals = circuit["totals"]
            assert isinstance(circuit, dict) and isinstance(totals, dict)
            totals["elapsed_seconds"] = (
                float(totals["elapsed_seconds"])
                + max(0.0, clock - float(consumed_at))
            )
            totals["unknown_provider_cost_entries"] = (
                int(totals["unknown_provider_cost_entries"]) + 1
            )
            self._archive_admission(record, finished_at=clock)
            open_reason = self._circuit_limit_reason(circuit)
            if open_reason is not None:
                self._open_circuit(record, now=clock, reason=open_reason)
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return record

    def _invalidate_from(
        self, record: dict[str, object], phase: str
    ) -> None:
        cutoff = _phase_index(phase)
        completed = record["completed_phases"]
        assert isinstance(completed, list)
        record["completed_phases"] = [
            item
            for item in completed
            if isinstance(item, dict)
            and _phase_index(str(item.get("phase"))) < cutoff
        ]
        if cutoff <= _phase_index("mutation"):
            record["candidate_digest"] = None

    def _block(
        self,
        record: dict[str, object],
        *,
        phase: str,
        outcome: str,
        evidence_digest: str,
        candidate_digest: str | None,
        integration_unchanged: bool | None,
        remote_unchanged: bool | None,
    ) -> None:
        resume_phase = phase
        if phase == "mutation":
            if candidate_digest is not None:
                raise ControlError(
                    "failed mutation must prove no candidate was produced"
                )
            self._invalidate_from(record, "mutation")
        elif phase == "security_review":
            if outcome == "technical_blocker":
                self._invalidate_from(record, "mutation")
                resume_phase = "mutation"
        elif phase in {"cross_review", "proof", "verification"}:
            self._invalidate_from(record, "mutation")
            resume_phase = "mutation"
        elif phase == "integration":
            if candidate_digest != record["candidate_digest"]:
                raise ControlError(
                    "integration failure candidate is not current"
                )
            if integration_unchanged is not True:
                record["status"] = "terminal_blocked"
                record["resume"] = None
                return
        elif phase == "push":
            if remote_unchanged is not True:
                record["status"] = "terminal_blocked"
                record["resume"] = None
                return
        elif phase not in {"plan_peer"}:
            raise ControlError("phase has no blocked-state transition")
        record["current_phase"] = resume_phase
        record["status"] = "blocked"
        record["resume"] = {
            "evidence_digest": evidence_digest,
            "outcome": outcome,
            "phase": resume_phase,
            "preconditions_digest": canonical_digest(
                {
                    "candidate": record["candidate_digest"],
                    "phase": resume_phase,
                    "plan": record["current_plan_digest"],
                }
            ),
            "reason": f"{phase}_{outcome}",
        }

    def finish(
        self,
        phase: str,
        *,
        admission_id: str,
        outcome: str,
        evidence_digest: str,
        provider_usd: float | None = None,
        candidate_digest: str | None = None,
        integration_unchanged: bool | None = None,
        remote_unchanged: bool | None = None,
        now: float | None = None,
    ) -> dict[str, object]:
        if outcome not in {
            "passed",
            "procedural_failure",
            "technical_blocker",
            "insufficient_context",
        }:
            raise ControlError("workflow outcome is unsupported")
        _require_digest(evidence_digest, "phase evidence digest")
        provider = (
            None
            if provider_usd is None
            else _nonnegative_number(provider_usd, "provider USD")
        )
        candidate = (
            None
            if candidate_digest is None
            else _require_digest(candidate_digest, "candidate digest")
        )
        clock = time.time() if now is None else now
        with _exclusive_record_lock(self.path):
            record = self._read()
            admission = record["admission"]
            if (
                not isinstance(admission, dict)
                or admission.get("admission_id") != admission_id
                or admission.get("phase") != phase
                or admission.get("state") != "consumed"
                or record["current_phase"] != phase
            ):
                raise ControlError(
                    "phase completion does not match a consumed admission"
                )
            consumed_at = admission.get("consumed_at")
            if (
                not isinstance(consumed_at, (int, float))
                or isinstance(consumed_at, bool)
                or not math.isfinite(float(consumed_at))
                or clock < float(consumed_at)
            ):
                raise ControlError("phase admission time is invalid")
            circuit = record["circuit"]
            totals = circuit["totals"]
            assert isinstance(circuit, dict) and isinstance(totals, dict)
            totals["elapsed_seconds"] = (
                float(totals["elapsed_seconds"])
                + clock
                - float(consumed_at)
            )
            if provider is None:
                totals["unknown_provider_cost_entries"] = (
                    int(totals["unknown_provider_cost_entries"]) + 1
                )
            else:
                totals["provider_usd"] = (
                    float(totals["provider_usd"]) + provider
                )
            if outcome == "procedural_failure":
                totals["procedural_failures"] = (
                    int(totals["procedural_failures"]) + 1
                )
            if outcome == "passed":
                if phase == "security_review":
                    if (
                        not isinstance(candidate, str)
                        or candidate != record["candidate_digest"]
                    ):
                        raise ControlError(
                            "passing security review candidate is not current"
                        )
                    security = SecurityReviewStore(
                        self.root
                    ).accepted_record(
                        evidence_digest,
                        executable_fingerprint=candidate,
                        workflow_binding_sha256=canonical_digest(
                            admission
                        ),
                    )
                    if security.get("accepted") is not True:
                        raise ControlError(
                            "passing security review lacks accepted "
                            "candidate-bound LaunchGuardian evidence: "
                            f"{security.get('reason', 'unknown reason')}"
                        )
                if phase == "mutation":
                    if candidate is None:
                        raise ControlError(
                            "passing mutation requires an exact candidate digest"
                        )
                    record["candidate_digest"] = candidate
                    circuit["worker_started"] = True
                elif _phase_index(phase) > _phase_index("mutation"):
                    if candidate != record["candidate_digest"]:
                        raise ControlError(
                            "passing phase candidate is not current"
                        )
                completed = record["completed_phases"]
                assert isinstance(completed, list)
                completed.append(
                    {
                        "candidate_digest": record["candidate_digest"],
                        "evidence_digest": evidence_digest,
                        "phase": phase,
                        "recorded_at": clock,
                    }
                )
                next_phase = _next_phase(
                    record["current_plan"], phase  # type: ignore[arg-type]
                )
                record["current_phase"] = next_phase
                record["resume"] = None
                record["status"] = (
                    "complete" if next_phase == "complete" else "active"
                )
            else:
                self._block(
                    record,
                    phase=phase,
                    outcome=outcome,
                    evidence_digest=evidence_digest,
                    candidate_digest=candidate,
                    integration_unchanged=integration_unchanged,
                    remote_unchanged=remote_unchanged,
                )
            self._archive_admission(record, finished_at=clock)
            open_reason = self._circuit_limit_reason(circuit)
            if open_reason is not None and not circuit["open"]:
                self._open_circuit(record, now=clock, reason=open_reason)
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return record

    def resume(
        self,
        authority_value: object,
        plan_value: object,
        *,
        expected_task_id: str,
        now: float | None = None,
    ) -> dict[str, object]:
        clock = time.time() if now is None else now
        checked = preflight(
            authority_value,
            plan_value,
            expected_task_id=expected_task_id,
            now=clock,
        )
        authority = checked["authority"]
        plan = checked["plan"]
        assert isinstance(authority, dict) and isinstance(plan, dict)
        with _exclusive_record_lock(self.path):
            record = self._read()
            if record["status"] != "blocked" or record["circuit"]["open"]:  # type: ignore[index]
                raise ControlError(
                    "workflow is not resumable without circuit resolution"
                )
            if (
                checked["authority_scope_digest"]
                != record["authority_scope_digest"]
                or checked["plan_digest"] != record["current_plan_digest"]
                or plan != record["current_plan"]
            ):
                raise ControlError(
                    "blocked resume requires unchanged authority scope and plan"
                )
            resume = record["resume"]
            if not isinstance(resume, dict):
                raise ControlError("blocked workflow lacks a resume transition")
            binding = canonical_digest(
                {
                    "resume": resume,
                    "workflow": self._transition_binding("resume", checked),
                }
            )
            self.actions.consume(
                str(authority["owner_action_digest"]),
                objective_id=self.objective_id,
                transition="resume",
                binding_digest=binding,
                now=clock,
            )
            record["authority"] = authority
            record["authority_digest"] = checked["authority_digest"]
            record["current_phase"] = resume["phase"]
            record["resume"] = None
            record["status"] = "active"
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return record

    def resolve_circuit(
        self,
        authority_value: object,
        plan_value: object,
        *,
        expected_task_id: str,
        now: float | None = None,
    ) -> dict[str, object]:
        clock = time.time() if now is None else now
        checked = preflight(
            authority_value,
            plan_value,
            expected_task_id=expected_task_id,
            now=clock,
        )
        authority = checked["authority"]
        plan = checked["plan"]
        assert isinstance(authority, dict) and isinstance(plan, dict)
        with _exclusive_record_lock(self.path):
            record = self._read()
            circuit = record["circuit"]
            current = record["current_plan"]
            assert isinstance(circuit, dict) and isinstance(current, dict)
            snapshot = circuit.get("opening_snapshot")
            if not circuit.get("open") or not isinstance(snapshot, dict):
                raise ControlError("objective circuit is not open")
            if int(circuit["resolution_count"]) >= MAX_CIRCUIT_RESOLUTIONS:
                raise ControlError("objective circuit resolution limit is exhausted")
            changes = {
                "authority": checked["authority_scope_digest"]
                != snapshot.get("authority_scope_digest"),
                "mechanism": checked["mechanism_digest"]
                != snapshot.get("mechanism_digest"),
                "plan": checked["plan_digest"] != snapshot.get("plan_digest"),
            }
            if not any(changes.values()):
                raise ControlError(
                    "circuit resolution requires a changed authority scope, "
                    "plan, or mechanism"
                )
            snapshot_digest = _require_digest(
                snapshot.get("snapshot_digest"),  # type: ignore[arg-type]
                "circuit opening snapshot digest",
            )
            binding = self._transition_binding(
                "resolve", checked, snapshot_digest=snapshot_digest
            )
            self.actions.consume(
                str(authority["owner_action_digest"]),
                objective_id=self.objective_id,
                transition="resolve",
                binding_digest=binding,
                now=clock,
            )
            if changes["plan"]:
                self._replace_plan(record, checked, now=clock)
            elif plan != current:
                raise ControlError("unchanged plan digest does not match current plan")
            record["authority"] = authority
            record["authority_digest"] = checked["authority_digest"]
            record["authority_scope_digest"] = checked[
                "authority_scope_digest"
            ]
            record["mechanism_digest"] = checked["mechanism_digest"]
            record["task_id"] = authority["task_id"]
            circuit["open"] = False
            circuit["opened_at"] = None
            circuit["opening_snapshot"] = None
            circuit["resolution_count"] = int(circuit["resolution_count"]) + 1
            circuit["baseline"] = dict(circuit["totals"])  # type: ignore[arg-type]
            circuit["limits"] = dict(authority["circuit_limits"])  # type: ignore[arg-type]
            record.setdefault("resolution_history", [])
            history = record["resolution_history"]
            assert isinstance(history, list)
            history.append(
                {
                    "changes": changes,
                    "resolved_at": clock,
                    "resolver_owner_action_digest": authority[
                        "owner_action_digest"
                    ],
                    "snapshot_digest": snapshot_digest,
                }
            )
            self._reset_after_identity_change(record, checked, now=clock)
            record["updated_at"] = clock
            _atomic_json(self.path, record)
        return record


def parse_workflow_payload(text: str) -> tuple[object, object]:
    payload = _exact_keys(
        _strict_json_loads(text), {"authority", "plan"}, "workflow payload"
    )
    return payload["authority"], payload["plan"]


def _is_reparse_point(metadata: os.stat_result) -> bool:
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(metadata, "st_file_attributes", 0) & marker)


def _same_file_identity(
    first: os.stat_result, second: os.stat_result
) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_size,
        first.st_mtime_ns,
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_size,
        second.st_mtime_ns,
    )


def _is_under(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def consume_workflow_payload_file(
    path_value: Path,
    expected_sha256: str,
    *,
    state_directory: Path,
) -> tuple[object, object]:
    """Read/verify/parse one state-root payload and burn it on every outcome."""
    expected = _require_digest(
        expected_sha256, "workflow payload SHA-256"
    )
    root = state_directory.resolve(strict=True)
    path = path_value
    if not path.is_absolute():
        raise ControlError("workflow payload path must be absolute")
    try:
        resolved = path.resolve(strict=True)
        before = path.lstat()
    except OSError as exc:
        raise ControlError(f"workflow payload is unavailable: {exc}") from exc
    if (
        not _is_under(resolved, root)
        or resolved == root
        or path != resolved
        or not stat.S_ISREG(before.st_mode)
        or _is_reparse_point(before)
    ):
        raise ControlError(
            "workflow payload must be a canonical regular non-link state file"
        )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    body = b""
    read_error: Exception | None = None
    cleanup_identity_ok = True
    try:
        descriptor = os.open(str(path), flags)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or _is_reparse_point(opened)
                or not _same_file_identity(before, opened)
            ):
                raise ControlError(
                    "workflow payload identity changed before the bounded read"
                )
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, 16 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_WORKFLOW_PAYLOAD_BYTES:
                    raise ControlError(
                        "workflow payload exceeds the input byte bound"
                    )
                chunks.append(chunk)
            after = os.fstat(descriptor)
            if not _same_file_identity(opened, after):
                raise ControlError(
                    "workflow payload changed during the bounded read"
                )
            body = b"".join(chunks)
        finally:
            os.close(descriptor)
        current = path.lstat()
        if not _same_file_identity(after, current):
            cleanup_identity_ok = False
            raise ControlError(
                "workflow payload path identity changed after the bounded read"
            )
        if hashlib.sha256(body).hexdigest() != expected:
            raise ControlError("workflow payload SHA-256 is mismatched")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ControlError("workflow payload is not UTF-8") from exc
        result = parse_workflow_payload(text)
    except Exception as exc:
        read_error = exc
        result = None
    if cleanup_identity_ok:
        try:
            path.unlink()
        except OSError as exc:
            raise ControlError(
                f"workflow payload cleanup failed and was not ignored: {exc}"
            ) from exc
    if read_error is not None:
        raise read_error
    assert result is not None
    return result


def reap_stale_workflow_payloads(
    state_directory: Path, *, now: float | None = None
) -> list[str]:
    """Delete only expired regular non-link payloads from the owned directory."""
    root = state_directory.resolve(strict=True)
    payload_root = root / "payloads"
    if not payload_root.exists():
        return []
    if (
        payload_root.is_symlink()
        or not payload_root.is_dir()
        or not _is_under(payload_root.resolve(strict=True), root)
    ):
        raise ControlError("workflow payload directory is not trustworthy")
    clock = time.time() if now is None else now
    removed: list[str] = []
    for candidate in sorted(payload_root.iterdir(), key=lambda item: item.name):
        metadata = candidate.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or _is_reparse_point(metadata)
            or clock - metadata.st_mtime < PAYLOAD_RETENTION_SECONDS
        ):
            continue
        try:
            candidate.unlink()
        except OSError as exc:
            raise ControlError(
                f"stale workflow payload cleanup failed: {exc}"
            ) from exc
        removed.append(candidate.name)
    return removed
