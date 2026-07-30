#!/usr/bin/env python3
"""Bounded local state, resource envelopes, and proof identity for Drydock."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterable, Iterator, Mapping, Sequence


PHASES = (
    "plan_peer",
    "mutation",
    "cross_review",
    "proof",
    "security_review",
    "verification",
    "integration",
)
MAX_TERMINAL_BYTES = 64 * 1024
MAX_RECORD_BYTES = 128 * 1024
MAX_RESULT_AGE_SECONDS = 24 * 60 * 60
MAX_LAUNCHGUARDIAN_REPORT_BYTES = 4 * 1024 * 1024
RECORD_LOCK_LEASE_SECONDS = 60
SAFE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
PEER_REVIEW_NAME = re.compile(
    r"^claude-architecture-review-round-[1-9][0-9]*\.json$"
)
INJECTION_NAMES = frozenset(
    {"conftest.py", "sitecustomize.py", "usercustomize.py"}
)
BYTECODE_SUFFIXES = frozenset({".pyc", ".pyo"})
FINGERPRINT_VERSION = "drydock-repository-fingerprint-v2"
EXECUTABLE_DIGEST_DOMAIN = b"drydock executable surface v2\0"
EVIDENCE_DIGEST_DOMAIN = b"drydock packet evidence v2\0"
TASK_MARKER = re.compile(br"^([ \t]*-[ \t]*\[)([ xX])(\][ \t]+)")
LEGACY_TASK_MARKER = re.compile(r"^\s*-\s*\[[ xX]\]\s+")
AT_REST_SECRET = re.compile(
    r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*"
    r"[\"']?[A-Za-z0-9_./+=-]{12,}|"
    r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_=-]{16,})"
)
HIGH_IMPACT_PROPERTIES = frozenset(
    {
        "persistence",
        "permissions",
        "process_boundaries",
        "verification_semantics",
    }
)
EXPECTED_LAUNCHGUARDIAN_SCANNERS = (
    "api_surface",
    "frontend_exposure",
    "gitleaks",
    "semgrep",
    "trivy",
)
EXPECTED_LAUNCHGUARDIAN_SEVERITIES = (
    "critical",
    "high",
    "medium",
    "low",
    "info",
)
EXPECTED_LAUNCHGUARDIAN_FINDING_SOURCES = frozenset(
    {
        *EXPECTED_LAUNCHGUARDIAN_SCANNERS,
        "config",
        "config_discovery",
        "launch_policy",
    }
)
EXPECTED_LAUNCHGUARDIAN_FINDING_STATUSES = frozenset(
    {
        "open",
        "fixed",
        "accepted",
        "false_positive",
        "not_applicable",
        "needs_review",
    }
)
ACCEPTED_LAUNCHGUARDIAN_STATUSES = frozenset(
    {"APPROVED", "APPROVED_WITH_DISPOSITIONS"}
)
LAUNCHGUARDIAN_DISPOSITION_FIELDS = frozenset(
    {
        "source",
        "rule_id",
        "status",
        "reason",
        "evidence",
        "approved_by",
        "approved_on",
    }
)
LAUNCHGUARDIAN_EXTERNAL_SCANNERS = frozenset(
    {"gitleaks", "semgrep", "trivy"}
)
LAUNCHGUARDIAN_REVIEW_PLACEHOLDERS = frozenset(
    {
        "-",
        "?",
        "n/a",
        "na",
        "none",
        "not applicable",
        "tbd",
        "todo",
        "unknown",
    }
)
LAUNCHGUARDIAN_REPORT_FIELDS = frozenset(
    {
        "schema_name",
        "schema_version",
        "generated_at",
        "launchguardian_version",
        "target",
        "mode",
        "validation_mode",
        "scan_mode",
        "lgf_validation_skipped",
        "strict_scanners",
        "launch_status",
        "lgf_config_valid",
        "lgf_validation_status",
        "scanner_availability",
        "scanner_counts",
        "scanner_blocking_counts",
        "counts_by_severity",
        "counts_by_scanner",
        "counts_by_status",
        "counts_by_gate",
        "blocking_findings",
        "launchguardian_config",
        "blocked",
        "findings",
    }
)
SECURITY_REVIEW_RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_kind",
        "candidate_commit",
        "command_contract",
        "executable_path",
        "executable_sha256",
        "executable_surface_sha256",
        "fingerprint_version",
        "report_sha256",
        "acceptance",
        "elapsed_seconds",
        "owner_checkout_unchanged",
        "process_exit_code",
        "process_output_sha256",
        "recorded_at",
        "authenticated",
        "provenance_attested",
        "record_key",
        "workflow_binding_sha256",
    }
)
SECURITY_PROCEDURAL_RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_kind",
        "candidate_commit",
        "executable_path",
        "executable_sha256",
        "executable_surface_sha256",
        "fingerprint_version",
        "stage",
        "reason",
        "owner_checkout_unchanged",
        "process_exit_code",
        "process_output_sha256",
        "process_liveness",
        "timed_out",
        "recorded_at",
        "authenticated",
        "provenance_attested",
        "record_key",
        "workflow_binding_sha256",
    }
)
SECURITY_PROCEDURAL_STAGES = frozenset(
    {
        "launchguardian_unavailable",
        "launchguardian_timeout",
        "security_review_invalid",
    }
)


class EvidenceError(RuntimeError):
    """A fail-closed local orchestration evidence error."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_digest(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_DIGEST.fullmatch(value):
        raise EvidenceError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _procedural_stage_consistent(
    *,
    stage: object,
    executable_path: object,
    process_liveness: object,
    timed_out: object,
) -> bool:
    if stage == "launchguardian_unavailable":
        return (
            executable_path is None
            and process_liveness == "not_started"
            and timed_out is False
        )
    if stage == "launchguardian_timeout":
        return (
            isinstance(executable_path, str)
            and bool(executable_path)
            and process_liveness == "absent"
            and timed_out is True
        )
    if stage == "security_review_invalid":
        return timed_out is False
    return False


def _atomic_json(path: Path, value: object) -> None:
    body = _canonical_json(value)
    if len(body) > MAX_RECORD_BYTES:
        raise EvidenceError("orchestration state record exceeds its byte bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise EvidenceError("orchestration state record must not be a symlink")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic() + 1.0
        while True:
            try:
                os.replace(temporary, path)
                break
            except PermissionError as exc:
                if os.name != "nt" or time.monotonic() >= deadline:
                    raise EvidenceError(
                        "atomic state replacement remained unavailable"
                    ) from exc
                time.sleep(0.005)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _read_json(path: Path) -> dict[str, object]:
    try:
        metadata = os.stat(path, follow_symlinks=False)
        attributes = getattr(metadata, "st_file_attributes", 0)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or path.is_symlink()
            or attributes
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise EvidenceError(
                "orchestration state record is not a plain regular file"
            )
        raw = path.read_bytes()
        if len(raw) > MAX_RECORD_BYTES:
            raise EvidenceError("orchestration state record exceeds its byte bound")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"orchestration state is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("orchestration state root is not an object")
    return value


def _strict_json_bytes(body: bytes, label: str) -> dict[str, object]:
    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EvidenceError(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} root is not an object")
    return value


def _read_bounded_plain_bytes(
    path: Path, *, maximum: int, label: str
) -> bytes:
    try:
        before = os.stat(path, follow_symlinks=False)
        attributes = getattr(before, "st_file_attributes", 0)
        if (
            not stat.S_ISREG(before.st_mode)
            or path.is_symlink()
            or attributes
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise EvidenceError(f"{label} is not a plain regular file")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise EvidenceError(f"{label} is not a plain regular file")
            body = stream.read(maximum + 1)
        after = os.stat(path, follow_symlinks=False)
        if (
            getattr(before, "st_dev", None) != getattr(opened, "st_dev", None)
            or getattr(before, "st_ino", None) != getattr(opened, "st_ino", None)
            or getattr(after, "st_dev", None) != getattr(opened, "st_dev", None)
            or getattr(after, "st_ino", None) != getattr(opened, "st_ino", None)
        ):
            raise EvidenceError(f"{label} identity changed while it was read")
    except OSError as exc:
        raise EvidenceError(f"{label} is unreadable: {exc}") from exc
    if len(body) > maximum:
        raise EvidenceError(f"{label} exceeds its byte bound")
    return body


def _write_bounded_evidence_bytes(path: Path, body: bytes) -> None:
    if not body or len(body) > MAX_LAUNCHGUARDIAN_REPORT_BYTES:
        raise EvidenceError("LaunchGuardian report size is outside its bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _read_bounded_plain_bytes(
            path,
            maximum=MAX_LAUNCHGUARDIAN_REPORT_BYTES,
            label="LaunchGuardian report digest path",
        )
        if existing != body:
            raise EvidenceError(
                "LaunchGuardian report digest path contains different bytes"
            )
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


@contextlib.contextmanager
def _exclusive_record_lock(path: Path) -> Iterator[None]:
    lock = path.with_name(f".{path.name}.lock")
    identity = process_identity(os.getpid())
    if identity is None:
        raise EvidenceError("cannot establish process identity for state lock")
    payload = _canonical_json({"process": identity, "created_at": time.time()})
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = lock.open("x+b")
        created = True
    except FileExistsError:
        try:
            stream = lock.open("r+b")
        except OSError as exc:
            raise EvidenceError(
                "orchestration state lock is unreadable"
            ) from exc
        created = False
    acquired = False
    owns_record = False
    try:
        if not _try_advisory_lock(stream):
            raise EvidenceError(
                "orchestration state is locked; refusing a concurrent update"
            )
        acquired = True
        if created:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            owns_record = True
        else:
            recoverable = False
            try:
                stream.seek(0)
                raw = stream.read(MAX_RECORD_BYTES + 1)
                if len(raw) > MAX_RECORD_BYTES:
                    raise ValueError("lock record exceeds its byte bound")
                existing = json.loads(raw.decode("utf-8"))
                if not isinstance(existing, dict):
                    raise ValueError("lock record root is not an object")
                created_at = existing.get("created_at")
                age = (
                    time.time() - float(created_at)
                    if isinstance(created_at, (int, float))
                    and not isinstance(created_at, bool)
                    and math.isfinite(float(created_at))
                    else math.inf
                )
                liveness = exact_process_liveness(existing.get("process"))
                recoverable = (
                    liveness in {"absent", "mismatched", "unknown"}
                    or age < 0
                    or age > RECORD_LOCK_LEASE_SECONDS
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, OSError):
                recoverable = True
            if not recoverable:
                raise EvidenceError(
                    "orchestration state is locked; refusing a live update"
                )
            stream.seek(0)
            stream.truncate()
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            owns_record = True
        yield
    finally:
        if owns_record:
            with contextlib.suppress(OSError):
                stream.seek(0)
                stream.truncate()
                stream.write(
                    _canonical_json(
                        {"released": True, "released_at": time.time()}
                    )
                )
                stream.flush()
                os.fsync(stream.fileno())
        if acquired:
            _release_advisory_lock(stream)
        stream.close()


def _try_advisory_lock(stream: BinaryIO) -> bool:
    try:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _release_advisory_lock(stream: BinaryIO) -> None:
    with contextlib.suppress(OSError):
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def state_root(
    override: Path | None = None, *, repository_root: Path | None = None
) -> Path:
    configured = override
    if configured is None:
        environment = os.environ.get("DRYDOCK_ORCHESTRATION_STATE_DIR")
        configured = Path(environment) if environment else None
    if configured is None:
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        else:
            base = Path(
                os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
            )
        configured = base / "Drydock" / "orchestration"
    resolved = configured.expanduser().resolve(strict=False)
    if repository_root is not None:
        repository = repository_root.resolve(strict=True)
        if resolved == repository or repository in resolved.parents:
            raise EvidenceError("orchestration state must remain outside the repository")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved.resolve(strict=True)


def _windows_process_token(pid: int) -> str | None:
    from ctypes import wintypes

    process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not process:
        return None
    try:
        created = wintypes.FILETIME()
        exited = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetProcessTimes(
            process,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        value = (created.dwHighDateTime << 32) | created.dwLowDateTime
        return str(value)
    finally:
        ctypes.windll.kernel32.CloseHandle(process)


def process_identity(pid: int) -> dict[str, object] | None:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        return None
    if os.name == "nt":
        token = _windows_process_token(pid)
    else:
        token = None
        with contextlib.suppress(OSError, IndexError):
            fields = (Path("/proc") / str(pid) / "stat").read_text(
                encoding="ascii"
            ).split()
            token = fields[21]
    return {"pid": pid, "started": token} if token is not None else None


def exact_process_liveness(identity: object) -> str:
    if not isinstance(identity, dict) or set(identity) != {"pid", "started"}:
        return "unknown"
    pid = identity.get("pid")
    started = identity.get("started")
    if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(
        started, str
    ):
        return "unknown"
    current = process_identity(pid)
    if current is None:
        return "absent"
    return "alive" if current == identity else "mismatched"


@dataclass(frozen=True)
class Envelope:
    elapsed_seconds: float
    calls: int
    input_bytes: int
    provider_usd: float

    def __post_init__(self) -> None:
        numeric = (self.elapsed_seconds, self.provider_usd)
        if (
            any(not math.isfinite(value) or value <= 0 for value in numeric)
            or isinstance(self.calls, bool)
            or self.calls < 1
            or isinstance(self.input_bytes, bool)
            or self.input_bytes < 1
        ):
            raise EvidenceError("resource envelope values must be positive and finite")


DEFAULT_PHASE_ENVELOPE = Envelope(600.0, 2, 64 * 1024, 2.0)
DEFAULT_RUN_ENVELOPE = Envelope(3600.0, 12, 1024 * 1024, 12.0)


def _empty_usage() -> dict[str, object]:
    return {
        "elapsed_seconds": 0.0,
        "calls": 0,
        "input_bytes": 0,
        "configured_provider_usd": 0.0,
        "observed_provider_usd": 0.0,
        "token_usage": "unknown",
        "account_usage": "unknown",
    }


class RunLedger:
    """Durable cumulative and per-phase envelope accounting."""

    def __init__(self, root: Path, run_id: str):
        if not isinstance(run_id, str) or not re.fullmatch(
            r"[0-9a-f]{32}", run_id
        ):
            raise EvidenceError("run ID has an invalid format")
        self.root = root.resolve(strict=True)
        self.run_id = run_id
        self.path = self.root / "runs" / f"{run_id}.json"

    @classmethod
    def start(
        cls,
        root: Path,
        *,
        objective_digest: str,
        owner_action_digest: str,
        previous_run_id: str | None = None,
        phase_envelopes: Mapping[str, Envelope] | None = None,
        run_envelope: Envelope = DEFAULT_RUN_ENVELOPE,
        now: float | None = None,
    ) -> "RunLedger":
        _require_digest(objective_digest, "objective digest")
        _require_digest(owner_action_digest, "Owner action digest")
        timestamp = time.time() if now is None else now
        run_id = uuid.uuid4().hex
        ledger = cls(root, run_id)
        phases = {
            phase: {
                "limit": asdict(
                    (phase_envelopes or {}).get(
                        phase, DEFAULT_PHASE_ENVELOPE
                    )
                ),
                "usage": _empty_usage(),
            }
            for phase in PHASES
        }
        transition = {
            "old_run_id": previous_run_id,
            "new_run_id": run_id,
            "timestamp": timestamp,
            "owner_action_digest": owner_action_digest,
        }
        record = {
            "schema_version": 1,
            "run_id": run_id,
            "objective_digest": objective_digest,
            "status": "active",
            "started_at": timestamp,
            "updated_at": timestamp,
            "run_limit": asdict(run_envelope),
            "usage": _empty_usage(),
            "phases": phases,
            "transition": transition,
            "reservations": {},
        }
        def write_new() -> None:
            ledger.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with ledger.path.open("xb") as stream:
                    body = _canonical_json(record)
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise EvidenceError("generated run ID already exists") from exc

        if previous_run_id is None:
            write_new()
        else:
            previous = cls(root, previous_run_id)
            with _exclusive_record_lock(previous.path):
                old = previous.read()
                if old.get("status") != "active":
                    raise EvidenceError("only an active run may be superseded")
                write_new()
                try:
                    old["status"] = "superseded"
                    old["updated_at"] = timestamp
                    old["superseded_by"] = run_id
                    old["owner_action_digest"] = owner_action_digest
                    _atomic_json(previous.path, old)
                except Exception:
                    with contextlib.suppress(FileNotFoundError):
                        ledger.path.unlink()
                    raise
        return ledger

    def read(self) -> dict[str, object]:
        return _read_json(self.path)

    def reserve(
        self,
        phase: str,
        *,
        input_bytes: int,
        configured_provider_usd: float,
        model: str,
        now: float | None = None,
    ) -> dict[str, object]:
        if phase not in PHASES:
            raise EvidenceError("phase is outside the supported envelope set")
        if (
            isinstance(input_bytes, bool)
            or input_bytes < 0
            or not isinstance(configured_provider_usd, (int, float))
            or isinstance(configured_provider_usd, bool)
            or not math.isfinite(configured_provider_usd)
            or configured_provider_usd < 0
        ):
            raise EvidenceError("reservation usage must be non-negative and finite")
        with _exclusive_record_lock(self.path):
            record = self.read()
            if record.get("status") != "active":
                return {"ok": False, "stage": "run_not_active"}
            timestamp = time.time() if now is None else now
            phase_record = record["phases"][phase]  # type: ignore[index]
            phase_usage = phase_record["usage"]
            run_usage = record["usage"]
            run_usage["elapsed_seconds"] = max(
                float(run_usage["elapsed_seconds"]),
                max(0.0, timestamp - float(record["started_at"])),
            )
            phase_limit = phase_record["limit"]
            run_limit = record["run_limit"]
            additions = {
                "calls": 1,
                "input_bytes": input_bytes,
                "configured_provider_usd": float(configured_provider_usd),
            }
            exhausted: list[str] = []
            if phase_usage["elapsed_seconds"] >= phase_limit["elapsed_seconds"]:
                exhausted.append("phase.elapsed_seconds")
            if run_usage["elapsed_seconds"] >= run_limit["elapsed_seconds"]:
                exhausted.append("run.elapsed_seconds")
            for key, addition in additions.items():
                limit_key = (
                    "provider_usd"
                    if key == "configured_provider_usd"
                    else key
                )
                if phase_usage[key] + addition > phase_limit[limit_key]:
                    exhausted.append(f"phase.{limit_key}")
                if run_usage[key] + addition > run_limit[limit_key]:
                    exhausted.append(f"run.{limit_key}")
            if exhausted:
                return {
                    "ok": False,
                    "stage": "envelope_exhausted",
                    "exhausted": exhausted,
                    "routes": [
                        "smaller_scope",
                        "advisory_only_right_sized_model",
                        "return_to_owner",
                    ],
                    "gate_effect": "none",
                }
            reservation_id = uuid.uuid4().hex
            started = timestamp
            for key, addition in additions.items():
                phase_usage[key] += addition
                run_usage[key] += addition
            record["reservations"][reservation_id] = {  # type: ignore[index]
                "phase": phase,
                "started_at": started,
                "model": model,
                "input_bytes": input_bytes,
                "configured_provider_usd": float(configured_provider_usd),
                "gate_eligible": True,
            }
            record["updated_at"] = started
            _atomic_json(self.path, record)
        return {"ok": True, "reservation_id": reservation_id}

    def complete(
        self,
        reservation_id: str,
        *,
        observed_provider_usd: float | None,
        token_usage: object = None,
        account_usage: object = None,
        now: float | None = None,
    ) -> dict[str, object]:
        with _exclusive_record_lock(self.path):
            record = self.read()
            reservations = record.get("reservations")
            if (
                not isinstance(reservations, dict)
                or reservation_id not in reservations
            ):
                raise EvidenceError("reservation is absent or already completed")
            reservation = reservations.pop(reservation_id)
            assert isinstance(reservation, dict)
            phase = reservation["phase"]
            finished = time.time() if now is None else now
            elapsed = max(0.0, finished - float(reservation["started_at"]))
            cost_known = (
                isinstance(observed_provider_usd, (int, float))
                and not isinstance(observed_provider_usd, bool)
                and math.isfinite(observed_provider_usd)
                and observed_provider_usd >= 0
            )
            phase_usage = record["phases"][phase]["usage"]  # type: ignore[index]
            run_usage = record["usage"]  # type: ignore[assignment]
            phase_usage["elapsed_seconds"] += elapsed
            run_usage["elapsed_seconds"] = max(
                float(run_usage["elapsed_seconds"]),
                max(0.0, finished - float(record["started_at"])),
            )
            for usage in (run_usage, phase_usage):
                if cost_known:
                    usage["observed_provider_usd"] += float(
                        observed_provider_usd
                    )
                usage["token_usage"] = (
                    token_usage if token_usage is not None else "unknown"
                )
                usage["account_usage"] = (
                    account_usage if account_usage is not None else "unknown"
                )
            record["updated_at"] = finished
            _atomic_json(self.path, record)
        return {
            "elapsed_seconds": elapsed,
            "provider_cost": (
                float(observed_provider_usd) if cost_known else "unknown"
            ),
            "phase": record["phases"][phase],  # type: ignore[index]
            "run": {
                "limit": record["run_limit"],
                "usage": record["usage"],
            },
        }

    def close(
        self, status: str, *, owner_action_digest: str | None = None
    ) -> None:
        allowed = {"complete", "blocked", "cancelled_by_owner"}
        if status not in allowed:
            raise EvidenceError("run terminal status is invalid")
        if status == "cancelled_by_owner":
            _require_digest(owner_action_digest or "", "Owner action digest")
        with _exclusive_record_lock(self.path):
            record = self.read()
            record["status"] = status
            record["updated_at"] = time.time()
            if owner_action_digest is not None:
                record["owner_action_digest"] = owner_action_digest
            _atomic_json(self.path, record)


def objective_critique_requirement(properties: Iterable[str]) -> dict[str, object]:
    normalized = {item for item in properties if isinstance(item, str)}
    matched = sorted(normalized & HIGH_IMPACT_PROPERTIES)
    return {
        "mode": "FULL" if matched else "unchanged",
        "critique_required": bool(matched),
        "matched_properties": matched,
    }


def critique_skipped(reason: str) -> dict[str, object]:
    if not isinstance(reason, str) or not reason.strip():
        raise EvidenceError("critique skip reason must not be empty")
    return {
        "critique_skipped": True,
        "reason": reason.strip(),
        "peer_convergence": "not_established",
        "gate_satisfied": False,
    }


class InvocationStore:
    """Atomic single-flight records with bounded terminal recovery."""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True) / "invocations"
        self.root.mkdir(parents=True, exist_ok=True)
        self.expire()

    def _path(self, fingerprint: str) -> Path:
        return self.root / f"{_require_digest(fingerprint, 'request fingerprint')}.json"

    @staticmethod
    def fingerprint(
        *,
        candidate: str,
        request_digest: str,
        model: str,
        schema_digest: str,
        configuration_digest: str,
        run_id: str,
    ) -> str:
        value = {
            "candidate": candidate,
            "request": _require_digest(request_digest, "request digest"),
            "model": model,
            "schema": _require_digest(schema_digest, "schema digest"),
            "configuration": _require_digest(
                configuration_digest, "configuration digest"
            ),
            "run_id": run_id,
        }
        return _digest_bytes(_canonical_json(value))

    def expire(self, *, now: float | None = None) -> None:
        timestamp = time.time() if now is None else now
        for path in self.root.glob("*.json"):
            with contextlib.suppress(EvidenceError, OSError):
                record = _read_json(path)
                observed = record.get("observed_at")
                if (
                    record.get("state") == "terminal"
                    and isinstance(observed, (int, float))
                    and timestamp - float(observed) > MAX_RESULT_AGE_SECONDS
                ):
                    record.pop("body", None)
                    record["state"] = "stale"
                    record["stale_at"] = timestamp
                    _atomic_json(path, record)

    def prepare(
        self,
        fingerprint: str,
        *,
        lease_seconds: float,
        now: float | None = None,
    ) -> dict[str, object]:
        self.expire(now=now)
        timestamp = time.time() if now is None else now
        identity = process_identity(os.getpid())
        if identity is None:
            return {
                "action": "return_to_owner",
                "stage": "process_identity_unproven",
            }
        path = self._path(fingerprint)
        record = {
            "schema_version": 1,
            "fingerprint": fingerprint,
            "state": "running",
            "process": identity,
            "started_at": timestamp,
            "lease_expires_at": timestamp + lease_seconds,
            "store_authentication": "none_user_writable",
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(_canonical_json(record))
                stream.flush()
                os.fsync(stream.fileno())
            return {"action": "start", "fingerprint": fingerprint}
        except FileExistsError:
            existing = _read_json(path)
        state = existing.get("state")
        if state == "terminal" and "body" in existing:
            return {
                "action": "recover",
                "fingerprint": fingerprint,
                "body": existing["body"],
                "observed_at": existing.get("observed_at"),
                "authenticated": False,
            }
        if state == "stale":
            return {
                "action": "return_to_owner",
                "stage": "stale_terminal_result",
                "observed_at": existing.get("observed_at"),
            }
        if state == "terminal":
            return {
                "action": "return_to_owner",
                "stage": "terminal_result_not_persisted",
                "terminal": existing.get("terminal"),
                "digest": existing.get("body_sha256"),
            }
        liveness = exact_process_liveness(existing.get("process"))
        lease = existing.get("lease_expires_at")
        if (
            liveness == "alive"
            and isinstance(lease, (int, float))
            and timestamp <= float(lease)
        ):
            return {
                "action": "attach",
                "stage": "equivalent_invocation_active",
                "fingerprint": fingerprint,
                "process": existing.get("process"),
            }
        return {
            "action": "return_to_owner",
            "stage": "indeterminate_interrupted_call",
            "fingerprint": fingerprint,
            "process_liveness": liveness,
            "automatic_restart": False,
        }

    def terminal(
        self,
        fingerprint: str,
        body: object,
        *,
        classification: str,
        reason: str,
        now: float | None = None,
    ) -> dict[str, object]:
        path = self._path(fingerprint)
        existing = _read_json(path)
        if existing.get("state") != "running":
            raise EvidenceError("invocation is not in a running state")
        canonical = _canonical_json(body)
        observed = time.time() if now is None else now
        eligible = len(canonical) <= MAX_TERMINAL_BYTES and not AT_REST_SECRET.search(
            canonical.decode("utf-8", "replace")
        )
        record = {
            "schema_version": 1,
            "fingerprint": fingerprint,
            "state": "terminal",
            "observed_at": observed,
            "expires_at": observed + MAX_RESULT_AGE_SECONDS,
            "terminal": classification[:128],
            "reason": reason[:500],
            "body_sha256": _digest_bytes(canonical),
            "store_authentication": "none_user_writable",
        }
        if eligible:
            record["body"] = body
            status = "persisted"
        else:
            status = "terminal_result_not_persisted"
        _atomic_json(path, record)
        return {
            "status": status,
            "body_sha256": record["body_sha256"],
            "observed_at": observed,
        }


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in list(environment):
        if key.upper().startswith("GIT_"):
            environment.pop(key)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _git_executable() -> str:
    executable = shutil.which("git")
    if not executable:
        raise EvidenceError("Git executable is unavailable")
    return executable


def _resolved_git_path(repo: Path) -> Path:
    try:
        return repo.resolve(strict=True)
    except OSError as exc:
        raise EvidenceError(f"Git repository path could not be resolved: {exc}") from exc


def _git_arguments(resolved_repo: Path, arguments: Sequence[str]) -> list[str]:
    return [
        _git_executable(),
        "-c",
        f"safe.directory={resolved_repo.as_posix()}",
        *arguments,
    ]


def _git(repo: Path, arguments: Sequence[str]) -> bytes:
    resolved_repo = _resolved_git_path(repo)
    try:
        result = subprocess.run(
            _git_arguments(resolved_repo, arguments),
            cwd=resolved_repo,
            capture_output=True,
            timeout=60,
            check=False,
            env=_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceError(f"Git command could not run: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace")[-500:].strip()
        raise EvidenceError(f"Git command failed: {detail}")
    return result.stdout


@dataclass(frozen=True)
class GitTreeEntry:
    path: str
    path_bytes: bytes
    mode: str
    object_type: str
    object_id: str
    body: bytes

    @property
    def kind(self) -> bytes:
        if self.mode in {"100644", "100755"} and self.object_type == "blob":
            return b"file"
        if self.mode == "120000" and self.object_type == "blob":
            return b"symlink"
        raise EvidenceError(
            f"tracked path has an unsupported Git type/mode: "
            f"{self.path} ({self.object_type} {self.mode})"
        )


def _git_tree_entries(repo: Path, commit: str = "HEAD") -> list[GitTreeEntry]:
    resolved_repo = _resolved_git_path(repo)
    raw = _git(resolved_repo, ["ls-tree", "-r", "-z", "--full-tree", commit])
    metadata: list[tuple[bytes, str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, path_bytes = record.split(b"\t", 1)
            mode_bytes, type_bytes, object_id_bytes = header.split(b" ", 2)
            mode = mode_bytes.decode("ascii")
            object_type = type_bytes.decode("ascii")
            object_id = object_id_bytes.decode("ascii")
        except (ValueError, UnicodeDecodeError) as exc:
            raise EvidenceError("Git tree contains malformed metadata") from exc
        path = path_bytes.decode("utf-8", "surrogateescape")
        metadata.append((path_bytes, mode, object_type, object_id))

    unsupported = [
        path_bytes.decode("utf-8", "surrogateescape")
        for path_bytes, mode, object_type, _ in metadata
        if not (
            object_type == "blob"
            and mode in {"100644", "100755", "120000"}
        )
    ]
    if unsupported:
        raise EvidenceError(
            "Git tree contains unsupported tracked types: "
            + ", ".join(unsupported[:10])
        )

    request = b"".join(
        object_id.encode("ascii") + b"\n"
        for _, _, _, object_id in metadata
    )
    try:
        result = subprocess.run(
            _git_arguments(resolved_repo, ["cat-file", "--batch"]),
            cwd=resolved_repo,
            input=request,
            capture_output=True,
            timeout=60,
            check=False,
            env=_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceError(f"Git object read could not run: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace")[-500:].strip()
        raise EvidenceError(f"Git object read failed: {detail}")

    bodies: list[bytes] = []
    cursor = 0
    for _, _, expected_type, expected_id in metadata:
        header_end = result.stdout.find(b"\n", cursor)
        if header_end < 0:
            raise EvidenceError("Git object batch ended before its header")
        header = result.stdout[cursor:header_end].split()
        if len(header) != 3:
            raise EvidenceError("Git object batch returned malformed metadata")
        object_id, object_type, size_bytes = header
        try:
            size = int(size_bytes)
        except ValueError as exc:
            raise EvidenceError("Git object batch returned an invalid size") from exc
        start = header_end + 1
        end = start + size
        if end >= len(result.stdout) or result.stdout[end : end + 1] != b"\n":
            raise EvidenceError("Git object batch returned a truncated body")
        if (
            object_id.decode("ascii") != expected_id
            or object_type.decode("ascii") != expected_type
        ):
            raise EvidenceError("Git object batch identity did not match the tree")
        bodies.append(result.stdout[start:end])
        cursor = end + 1
    if cursor != len(result.stdout):
        raise EvidenceError("Git object batch returned trailing data")

    return [
        GitTreeEntry(
            path=path_bytes.decode("utf-8", "surrogateescape"),
            path_bytes=path_bytes,
            mode=mode,
            object_type=object_type,
            object_id=object_id,
            body=body,
        )
        for (path_bytes, mode, object_type, object_id), body in zip(
            metadata, bodies
        )
    ]


def _packet_evidence_path(path: str, packet_root: str | None) -> bool:
    if packet_root is None:
        return False
    pure = PurePosixPath(path)
    root = PurePosixPath(packet_root)
    if pure.parent != root:
        return False
    return (
        pure.name == "verification.md"
        or pure.name == "codex-final-verifier.json"
        or PEER_REVIEW_NAME.fullmatch(pure.name) is not None
    )


def _valid_peer_summary(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    expected = {
        "schema_version",
        "evidence_kind",
        "converged",
        "overall",
        "blocking_concerns",
        "gaps",
        "risks",
        "required_changes",
    }
    return (
        set(value) == expected
        and value.get("schema_version") == 1
        and value.get("evidence_kind") == "peer_review_summary"
        and isinstance(value.get("converged"), bool)
        and isinstance(value.get("overall"), str)
        and all(
            isinstance(value.get(key), list)
            and len(value[key]) <= 64
            and all(
                isinstance(item, str) and 0 < len(item) <= 12000
                for item in value[key]
            )
            for key in ("blocking_concerns", "gaps", "risks", "required_changes")
        )
    )


def _valid_final_verifier(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    expected = {
        "schema_version",
        "evidence_kind",
        "verdict",
        "overall",
        "blockers",
        "gaps",
        "risks",
    }
    return (
        set(value) == expected
        and value.get("schema_version") == 1
        and value.get("evidence_kind") == "codex_final_verifier"
        and value.get("verdict") in {"PASS", "BLOCKED"}
        and isinstance(value.get("overall"), str)
        and all(
            isinstance(value.get(key), list)
            and len(value[key]) <= 64
            and all(
                isinstance(item, str) and 0 < len(item) <= 12000
                for item in value[key]
            )
            for key in ("blockers", "gaps", "risks")
        )
    )


def _valid_packet_json_bytes(name: str, body: bytes) -> bool:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if PurePosixPath(name).name == "codex-final-verifier.json":
        return _valid_final_verifier(value)
    return _valid_peer_summary(value)


def _canonical_repo_relative(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvidenceError(f"{label} must be a canonical repository-relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise EvidenceError(f"{label} must be a canonical repository-relative path")
    if pure.as_posix() != value:
        raise EvidenceError(f"{label} must be a canonical repository-relative path")
    return value


def _update_tree_digest(
    digest: object, entry: GitTreeEntry, body: bytes
) -> None:
    for field in (
        entry.path_bytes,
        entry.kind,
        entry.mode.encode("ascii"),
        body,
    ):
        digest.update(len(field).to_bytes(8, "big"))
        digest.update(field)


def _project_tasks(body: bytes) -> tuple[bytes | None, str]:
    if body.startswith(b"\xef\xbb\xbf"):
        return None, "leading UTF-8 BOM is not canonical"
    if b"\r" in body:
        return None, "CR bytes are not canonical"
    try:
        text_lines = body.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        return None, "tasks bytes are not valid UTF-8"
    byte_lines = body.split(b"\n")
    normalized: list[bytes] = []
    for byte_line, text_line in zip(byte_lines, text_lines):
        canonical = TASK_MARKER.match(byte_line)
        legacy = LEGACY_TASK_MARKER.match(text_line)
        if legacy is not None and canonical is None:
            return None, "legacy task marker is outside the canonical ASCII grammar"
        if canonical is None:
            normalized.append(byte_line)
            continue
        normalized.append(
            canonical.group(1)
            + b" "
            + canonical.group(3)
            + byte_line[canonical.end() :]
        )
    return b"\n".join(normalized), "applied"


def repository_fingerprints(
    repo: Path,
    *,
    packet_root: str | None = None,
    exclude_evidence_path: str | None = None,
) -> dict[str, object]:
    root = Path(
        _git(repo, ["rev-parse", "--show-toplevel"])
        .decode("utf-8", "replace")
        .strip()
    ).resolve(strict=True)
    status = _git(
        root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    head = _git(root, ["rev-parse", "HEAD"]).decode("ascii").strip()
    entries = _git_tree_entries(root, head)
    if packet_root is not None:
        packet_root = _canonical_repo_relative(packet_root, "packet root")
    if exclude_evidence_path is not None:
        exclude_evidence_path = _canonical_repo_relative(
            exclude_evidence_path, "excluded evidence path"
        )
    ignored = [
        item[3:].decode("utf-8", "surrogateescape")
        for item in _git(
            root,
            [
                "status",
                "--porcelain=v1",
                "-z",
                "--ignored=matching",
                "--untracked-files=all",
            ],
        ).split(b"\0")
        if item.startswith(b"!! ")
    ]
    executable = hashlib.sha256(EXECUTABLE_DIGEST_DOMAIN)
    evidence = hashlib.sha256(EVIDENCE_DIGEST_DOMAIN)
    tracked_bytecode: list[str] = []
    invalid_evidence: list[str] = []
    task_projection = {
        "path": (
            f"{packet_root}/tasks.md" if packet_root is not None else None
        ),
        "status": "not_requested",
        "reason": "packet root was not supplied",
    }
    task_path = task_projection["path"]
    task_matches = (
        [
            entry
            for entry in entries
            if task_path is not None
            and entry.path.casefold() == str(task_path).casefold()
        ]
        if task_path is not None
        else []
    )
    projected_task: GitTreeEntry | None = None
    projected_body: bytes | None = None
    if task_path is not None:
        if len(task_matches) != 1 or task_matches[0].path != task_path:
            task_projection = {
                "path": task_path,
                "status": "declined",
                "reason": (
                    "exact tracked tasks path is absent or has a case-fold "
                    "equivalent conflict"
                ),
            }
        elif task_matches[0].kind != b"file":
            task_projection = {
                "path": task_path,
                "status": "declined",
                "reason": "tracked tasks path is not a regular Git file",
            }
        else:
            projected_body, reason = _project_tasks(task_matches[0].body)
            if projected_body is None:
                task_projection = {
                    "path": task_path,
                    "status": "declined",
                    "reason": reason,
                }
            else:
                projected_task = task_matches[0]
                task_projection = {
                    "path": task_path,
                    "status": "applied",
                    "reason": "canonical task state is lifecycle evidence",
                }

    for entry in sorted(entries, key=lambda item: item.path_bytes):
        name = entry.path
        is_bytecode = (
            Path(name).suffix.casefold() in BYTECODE_SUFFIXES
            or "__pycache__" in PurePosixPath(name).parts
        )
        if is_bytecode:
            tracked_bytecode.append(name)
        if projected_task is not None and name == projected_task.path:
            _update_tree_digest(executable, entry, projected_body)
            _update_tree_digest(evidence, entry, entry.body)
            continue

        evidence_path = _packet_evidence_path(name, packet_root)
        if evidence_path and (
            entry.kind != b"file"
            or (
                PurePosixPath(name).suffix == ".json"
                and not _valid_packet_json_bytes(name, entry.body)
            )
        ):
            invalid_evidence.append(name)
            evidence_path = False
        if not (evidence_path and name == exclude_evidence_path):
            digest = evidence if evidence_path else executable
            _update_tree_digest(digest, entry, entry.body)
    ignored_injection = sorted(
        name
        for name in ignored
        if PurePosixPath(name.rstrip("/")).name.casefold() in INJECTION_NAMES
        or PurePosixPath(name.rstrip("/")).suffix.casefold() == ".pth"
    )
    return {
        "head": head,
        "fingerprint_version": FINGERPRINT_VERSION,
        "fingerprint_source": "exact committed Git tree and blob bytes",
        "executable_surface_sha256": executable.hexdigest(),
        "packet_evidence_sha256": evidence.hexdigest(),
        "packet_evidence_excluded_path": exclude_evidence_path,
        "task_projection": task_projection,
        "clean": not status,
        "tracked_bytecode": tracked_bytecode,
        "ignored_code_injection": ignored_injection,
        "invalid_packet_evidence": invalid_evidence,
        "reuse_eligible": (
            not status
            and not tracked_bytecode
            and not ignored_injection
            and not invalid_evidence
        ),
        "ignored_bytecode_blocks_reuse": False,
        "authenticated": False,
    }


@contextlib.contextmanager
def fresh_proof_root(repo: Path, commit: str) -> Iterator[Path]:
    tree = _git_tree_entries(repo, commit)
    expected = {entry.path: entry for entry in tree}
    archive = _git(repo, ["archive", "--format=tar", commit])
    with tempfile.TemporaryDirectory(prefix="drydock-proof-") as temporary:
        root = Path(temporary).resolve(strict=True)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
            observed: set[str] = set()
            for member in bundle.getmembers():
                candidate = PurePosixPath(member.name)
                if (
                    candidate.is_absolute()
                    or ".." in candidate.parts
                    or "\\" in member.name
                    or member.issym()
                    or member.islnk()
                    or not (member.isfile() or member.isdir())
                ):
                    raise EvidenceError("proof archive contains an unsafe path")
                if member.isdir():
                    continue
                entry = expected.get(member.name)
                if entry is None or entry.kind != b"file":
                    raise EvidenceError(
                        "proof archive path set differs from the committed Git tree"
                    )
                stream = bundle.extractfile(member)
                if stream is None or stream.read() != entry.body:
                    raise EvidenceError(
                        "proof archive bytes differ from the committed Git blob"
                    )
                archive_executable = bool(member.mode & 0o111)
                git_executable = entry.mode == "100755"
                if archive_executable != git_executable:
                    raise EvidenceError(
                        "proof archive mode differs from the committed Git mode"
                    )
                observed.add(member.name)
            if observed != set(expected):
                raise EvidenceError(
                    "proof archive path set differs from the committed Git tree"
                )
        for entry in tree:
            relative = PurePosixPath(entry.path)
            if (
                relative.is_absolute()
                or not relative.parts
                or any(part in {"", ".", ".."} for part in relative.parts)
                or "\\" in entry.path
                or (
                    os.name == "nt"
                    and any(":" in part for part in relative.parts)
                )
            ):
                raise EvidenceError(
                    "committed proof path cannot be safely materialized"
                )
            destination = root.joinpath(*relative.parts)
            resolved = destination.resolve(strict=False)
            if root not in resolved.parents:
                raise EvidenceError(
                    "committed proof path escapes the materialization root"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(entry.body)
            if os.name != "nt":
                destination.chmod(
                    0o755 if entry.mode == "100755" else 0o644
                )
        bytecode = [
            path
            for path in root.rglob("*")
            if path.is_file()
            and (
                path.suffix.casefold() in BYTECODE_SUFFIXES
                or "__pycache__" in path.parts
            )
        ]
        if bytecode:
            raise EvidenceError("fresh proof root contains bytecode")
        yield root


def command_environment_fingerprint(
    command: Sequence[str], environment: Mapping[str, str]
) -> str:
    return _digest_bytes(
        _canonical_json(
            {
                "command": list(command),
                "environment": dict(sorted(environment.items())),
            }
        )
    )


def run_proof_command(
    repo: Path,
    *,
    commit: str,
    command: Sequence[str],
    environment: Mapping[str, str] | None = None,
    timeout: int = 900,
) -> dict[str, object]:
    if not command or not all(isinstance(item, str) and item for item in command):
        raise EvidenceError("proof command must contain non-empty argv strings")
    if timeout < 1:
        raise EvidenceError("proof timeout must be positive")
    extra = dict(environment or {})
    proof_environment = os.environ.copy()
    proof_environment.update(extra)
    proof_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    with fresh_proof_root(repo, commit) as root:
        try:
            result = subprocess.run(
                list(command),
                cwd=root,
                capture_output=True,
                timeout=timeout,
                check=False,
                env=proof_environment,
            )
            timed_out = False
            output = result.stdout + result.stderr
            exit_code: int | None = result.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            output = (exc.stdout or b"") + (exc.stderr or b"")
            exit_code = None
    return {
        "commit": commit,
        "command": list(command),
        "environment_sha256": command_environment_fingerprint(
            command,
            {
                **extra,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        ),
        "elapsed_seconds": time.monotonic() - started,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "terminal_status": (
            "timeout" if timed_out else "passed" if exit_code == 0 else "failed"
        ),
        "output_sha256": _digest_bytes(output),
    }


def launchguardian_report_acceptance(
    report: Mapping[str, object], *, expected_target: Path | str
) -> dict[str, object]:
    def valid_count_map(
        value: object,
        *,
        exact_keys: set[str] | None = None,
    ) -> bool:
        return (
            isinstance(value, dict)
            and (exact_keys is None or set(value) == exact_keys)
            and all(isinstance(key, str) and key for key in value)
            and all(
                type(count) is int and count >= 0
                for count in value.values()
            )
        )

    if set(report) != LAUNCHGUARDIAN_REPORT_FIELDS:
        raise EvidenceError("LaunchGuardian report fields do not match schema 0.2.0")
    expected_root = (
        str(expected_target.resolve(strict=True))
        if isinstance(expected_target, Path)
        else expected_target
    )
    if (
        report.get("schema_name") != "launchguardian.report"
        or report.get("schema_version") != "0.2.0"
        or report.get("target") != expected_root
        or report.get("mode") != "framework"
        or report.get("validation_mode") != "framework"
        or report.get("scan_mode") != "local"
        or report.get("lgf_validation_skipped") is not False
        or report.get("strict_scanners") is not True
    ):
        raise EvidenceError(
            "LaunchGuardian report mode, target, or schema binding is invalid"
        )
    version = report.get("launchguardian_version")
    generated_at = report.get("generated_at")
    if (
        not isinstance(version, str)
        or not version
        or len(version) > 64
        or not isinstance(generated_at, str)
        or not generated_at
        or len(generated_at) > 128
    ):
        raise EvidenceError("LaunchGuardian report identity fields are invalid")
    availability = report.get("scanner_availability")
    scanner_counts = report.get("scanner_counts")
    blocking_counts = report.get("scanner_blocking_counts")
    blocking_findings = report.get("blocking_findings")
    findings = report.get("findings")
    scanner_keys = set(EXPECTED_LAUNCHGUARDIAN_SCANNERS)
    if (
        not isinstance(availability, dict)
        or set(availability) != scanner_keys
        or any(not isinstance(value, str) for value in availability.values())
        or not valid_count_map(scanner_counts, exact_keys=scanner_keys)
        or not valid_count_map(blocking_counts, exact_keys=scanner_keys)
        or not valid_count_map(
            report.get("counts_by_severity"),
            exact_keys=set(EXPECTED_LAUNCHGUARDIAN_SEVERITIES),
        )
        or not valid_count_map(report.get("counts_by_scanner"))
        or not valid_count_map(report.get("counts_by_status"))
        or not valid_count_map(report.get("counts_by_gate"))
        or not isinstance(blocking_findings, list)
        or any(not isinstance(item, dict) for item in blocking_findings)
        or not isinstance(findings, list)
        or any(not isinstance(item, dict) for item in findings)
        or len(findings) > 100_000
        or type(report.get("blocked")) is not bool
        or type(report.get("lgf_config_valid")) is not bool
        or not isinstance(report.get("lgf_validation_status"), str)
        or not isinstance(report.get("launch_status"), str)
        or not isinstance(report.get("launchguardian_config"), dict)
    ):
        raise EvidenceError(
            "LaunchGuardian scanner or finding collections are malformed"
        )
    required_finding_fields = {
        "blocks_launch": bool,
        "category": str,
        "disposition": (dict, type(None)),
        "related_gate": str,
        "rule_id": str,
        "severity": str,
        "source": str,
        "status": str,
        "title": str,
    }
    if any(
        any(
            field not in finding
            or (
                not isinstance(expected_type, tuple)
                and type(finding[field]) is not expected_type
            )
            or (
                isinstance(expected_type, tuple)
                and type(finding[field]) not in expected_type
            )
            for field, expected_type in required_finding_fields.items()
        )
        for finding in findings
    ):
        raise EvidenceError(
            "LaunchGuardian findings lack fields required to verify aggregates"
        )
    if any(
        not finding["category"]
        or not finding["source"]
        or not finding["status"]
        or not finding["title"]
        or finding["severity"] not in EXPECTED_LAUNCHGUARDIAN_SEVERITIES
        or finding["source"]
        not in EXPECTED_LAUNCHGUARDIAN_FINDING_SOURCES
        or finding["status"]
        not in EXPECTED_LAUNCHGUARDIAN_FINDING_STATUSES
        for finding in findings
    ):
        raise EvidenceError(
            "LaunchGuardian finding source, severity, or status is invalid"
        )
    config = report["launchguardian_config"]
    configured_dispositions = config.get("finding_dispositions")
    if not isinstance(configured_dispositions, list):
        raise EvidenceError(
            "LaunchGuardian disposition configuration is malformed"
        )

    def valid_review_text(value: object) -> bool:
        return (
            isinstance(value, str)
            and bool(value.strip())
            and value.strip().lower()
            not in LAUNCHGUARDIAN_REVIEW_PLACEHOLDERS
        )

    def valid_approval_date(value: object) -> bool:
        if not isinstance(value, str):
            return False
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False
        return parsed.isoformat() == value and parsed <= date.today()

    def valid_disposition(value: object) -> bool:
        return (
            isinstance(value, dict)
            and set(value) == LAUNCHGUARDIAN_DISPOSITION_FIELDS
            and value.get("source") == "semgrep"
            and isinstance(value.get("rule_id"), str)
            and bool(str(value["rule_id"]).strip())
            and not any(
                character in str(value["rule_id"])
                for character in "*?[]"
            )
            and value.get("status") == "not_applicable"
            and valid_review_text(value.get("reason"))
            and valid_review_text(value.get("evidence"))
            and valid_review_text(value.get("approved_by"))
            and valid_approval_date(value.get("approved_on"))
        )

    if any(not valid_disposition(item) for item in configured_dispositions):
        raise EvidenceError(
            "LaunchGuardian disposition configuration is malformed"
        )
    disposition_keys = [
        (str(item["source"]), str(item["rule_id"]))
        for item in configured_dispositions
    ]
    if len(disposition_keys) != len(set(disposition_keys)):
        raise EvidenceError(
            "LaunchGuardian disposition configuration has duplicate keys"
        )
    configured_disposition_keys = set(disposition_keys)
    applied_disposition_keys: set[tuple[str, str]] = set()
    for finding in findings:
        status = str(finding["status"])
        disposition = finding["disposition"]
        if status == "not_applicable":
            if (
                finding["source"] != "semgrep"
                or finding["severity"] == "critical"
                or not valid_disposition(disposition)
                or disposition not in configured_dispositions
                or disposition["source"] != finding["source"]
                or disposition["rule_id"] != finding["rule_id"]
                or disposition["status"] != status
                or finding["blocks_launch"]
                is not (finding["severity"] == "high")
            ):
                raise EvidenceError(
                    "LaunchGuardian finding disposition is invalid"
                )
            applied_disposition_keys.add(
                (str(finding["source"]), str(finding["rule_id"]))
            )
        elif disposition is not None:
            raise EvidenceError(
                "LaunchGuardian finding disposition contradicts its status"
            )
        elif status == "needs_review":
            if (
                finding["source"] != "config"
                or finding["category"] != "config_policy"
                or finding["title"]
                != "Configured finding disposition was not used"
                or finding["severity"] != "info"
                or finding["blocks_launch"] is not False
                or finding["rule_id"] != ""
            ):
                raise EvidenceError(
                    "LaunchGuardian needs-review finding is invalid"
                )
        elif status != "open":
            raise EvidenceError(
                "LaunchGuardian finding status is not produced by schema 0.2.0"
            )
        if finding["severity"] == "critical" and (
            status != "open"
            or finding["blocks_launch"] is not True
            or disposition is not None
        ):
            raise EvidenceError(
                "LaunchGuardian Critical finding semantics are invalid"
            )
    unused_disposition_descriptions = Counter(
        "No current finding matched the exact disposition key "
        f"{source}:{rule_id}."
        for source, rule_id in (
            configured_disposition_keys - applied_disposition_keys
        )
    )
    needs_review_findings = [
        finding for finding in findings if finding["status"] == "needs_review"
    ]
    if (
        any(
            not isinstance(finding.get("description"), str)
            for finding in needs_review_findings
        )
        or Counter(
            str(finding["description"])
            for finding in needs_review_findings
        )
        != unused_disposition_descriptions
    ):
        raise EvidenceError(
            "LaunchGuardian unused disposition evidence is invalid"
        )
    open_blockers = [
        finding
        for finding in findings
        if finding["blocks_launch"] is True and finding["status"] == "open"
    ]
    if blocking_findings != open_blockers:
        raise EvidenceError(
            "LaunchGuardian open-blocker summary contradicts its findings"
        )
    severity_counter = Counter(
        str(finding["severity"]) for finding in findings
    )
    expected_by_severity = {
        severity: severity_counter.get(severity, 0)
        for severity in EXPECTED_LAUNCHGUARDIAN_SEVERITIES
    }
    expected_by_scanner = dict(
        Counter(str(finding["source"]) for finding in findings)
    )
    expected_by_status = dict(
        Counter(str(finding["status"]) for finding in findings)
    )
    expected_by_gate = dict(
        Counter(
            str(finding["related_gate"]) or "Unmapped"
            for finding in findings
        )
    )
    if (
        report["counts_by_severity"] != expected_by_severity
        or report["counts_by_scanner"] != expected_by_scanner
        or report["counts_by_status"] != expected_by_status
        or report["counts_by_gate"] != expected_by_gate
        or report["blocked"] is not bool(open_blockers)
    ):
        raise EvidenceError(
            "LaunchGuardian aggregate counts contradict its findings"
        )
    scanner_states = {
        name: str(availability[name])
        for name in EXPECTED_LAUNCHGUARDIAN_SCANNERS
    }
    disabled = sorted(
        name for name, value in scanner_states.items() if value == "disabled"
    )
    unavailable = sorted(
        name
        for name, value in scanner_states.items()
        if value in {"unavailable", "failed"}
    )
    unexpected = sorted(
        name
        for name, value in scanner_states.items()
        if value
        not in {"ran", "disabled", "unavailable", "failed"}
    )
    if unexpected:
        raise EvidenceError(
            "LaunchGuardian scanner availability state is invalid"
        )
    for name, state in scanner_states.items():
        scanner_findings = [
            finding for finding in findings if finding["source"] == name
        ]
        expected_blocking_count = sum(
            1
            for finding in open_blockers
            if finding["source"] == name
        )
        if state == "ran":
            producer_shape_valid = all(
                finding["category"] != "scanner_unavailable"
                for finding in scanner_findings
            )
            expected_scanner_count = len(scanner_findings)
        elif state == "unavailable":
            producer_shape_valid = (
                name in LAUNCHGUARDIAN_EXTERNAL_SCANNERS
                and len(scanner_findings) == 1
                and scanner_findings[0]["category"] == "scanner_unavailable"
                and scanner_findings[0]["title"]
                == f"{name.replace('_', ' ').title()} scanner unavailable"
                and scanner_findings[0]["severity"] == "medium"
                and scanner_findings[0]["status"] == "open"
                and scanner_findings[0]["blocks_launch"] is True
                and scanner_findings[0]["rule_id"] == ""
                and scanner_findings[0]["disposition"] is None
            )
            expected_scanner_count = 0
        elif state == "failed":
            producer_shape_valid = not scanner_findings
            expected_scanner_count = 0
            expected_blocking_count = 0
        elif state == "disabled":
            disabled_title = (
                f"{name.replace('_', ' ').title()} scanner disabled by config"
            )
            disabled_findings = [
                finding
                for finding in findings
                if finding["source"] == "config"
                and finding["category"] == "scanner_disabled"
                and finding["title"] == disabled_title
            ]
            producer_shape_valid = (
                not scanner_findings
                and len(disabled_findings) == 1
                and disabled_findings[0]["status"] == "open"
                and disabled_findings[0]["rule_id"] == ""
                and disabled_findings[0]["disposition"] is None
                and disabled_findings[0]["severity"]
                == (
                    "high"
                    if disabled_findings[0]["blocks_launch"] is True
                    else "info"
                )
            )
            expected_scanner_count = 0
            expected_blocking_count = sum(
                1
                for finding in disabled_findings
                if finding["blocks_launch"] is True
                and finding["status"] == "open"
            )
        else:
            producer_shape_valid = not scanner_findings
            expected_scanner_count = 0
            expected_blocking_count = 0
        if (
            not producer_shape_valid
            or int(scanner_counts[name]) != expected_scanner_count
            or int(blocking_counts[name]) != expected_blocking_count
        ):
            raise EvidenceError(
                "LaunchGuardian scanner counts contradict its findings"
            )
    launch_status = report.get("launch_status")
    expected_lgf_validation_status = (
        "valid" if report["lgf_config_valid"] is True else "blocked"
    )
    expected_launch_status = (
        "BLOCKED"
        if open_blockers
        else "INCOMPLETE"
        if any(state != "ran" for state in scanner_states.values())
        else "APPROVED_WITH_DISPOSITIONS"
        if any(finding["disposition"] is not None for finding in findings)
        else "APPROVED"
    )
    if (
        report["lgf_validation_status"] != expected_lgf_validation_status
        or launch_status != expected_launch_status
    ):
        raise EvidenceError(
            "LaunchGuardian launch or LGF status contradicts its evidence"
        )
    technical_blocker = (
        report.get("lgf_config_valid") is not True
        or report.get("lgf_validation_status") != "valid"
        or report.get("blocked") is not False
        or bool(open_blockers)
        or bool(disabled)
        or any(int(value) > 0 for value in blocking_counts.values())
        or launch_status == "BLOCKED"
    )
    procedural_failure = (
        bool(unavailable)
        or bool(unexpected)
        or launch_status in {"INCOMPLETE", "SCANNED_WITHOUT_LGF"}
    )
    accepted = (
        not technical_blocker
        and not procedural_failure
        and launch_status in ACCEPTED_LAUNCHGUARDIAN_STATUSES
        and all(value == "ran" for value in scanner_states.values())
    )
    if accepted:
        outcome = "passed"
        reason = (
            "candidate-bound strict LaunchGuardian report is accepted with "
            "valid LGF, zero open blockers, and all expected scanners ran"
        )
    elif technical_blocker:
        outcome = "technical_blocker"
        reason = "LaunchGuardian reported a substantive candidate or policy blocker"
    else:
        outcome = "procedural_failure"
        reason = (
            "LaunchGuardian execution or scanner completeness is not proven"
        )
    return {
        "accepted": accepted,
        "workflow_outcome": outcome,
        "reason": reason,
        "launch_status": launch_status,
        "launchguardian_version": version,
        "lgf_config_valid": report.get("lgf_config_valid"),
        "lgf_validation_status": report.get("lgf_validation_status"),
        "scanner_availability": scanner_states,
        "scanner_blocking_counts": {
            name: int(blocking_counts[name])
            for name in EXPECTED_LAUNCHGUARDIAN_SCANNERS
        },
        "open_blocking_findings": len(open_blockers),
    }


def _validate_launchguardian_command_contract(
    command_contract: Sequence[str],
    *,
    executable_path: str,
    expected_target: str,
) -> list[str]:
    command = list(command_contract)
    if (
        len(command) != 8
        or not all(isinstance(item, str) and item for item in command)
        or not Path(executable_path).is_absolute()
        or command[0] != executable_path
        or command[1:3] != ["scan", "--target"]
        or command[3] != expected_target
        or command[4:7]
        != ["--framework-mode", "--strict-scanners", "--output-dir"]
        or not Path(command[7]).is_absolute()
    ):
        raise EvidenceError(
            "security command is not the fixed strict LaunchGuardian contract"
        )
    return command


class SecurityReviewStore:
    """Candidate-bound LaunchGuardian evidence; user-writable, never attestation."""

    def __init__(self, root: Path):
        state = root.resolve(strict=True)
        self.record_root = state / "security-reviews"
        self.report_root = state / "security-reports"

    def record(
        self,
        *,
        candidate_commit: str,
        executable_fingerprint: str,
        executable_path: str,
        executable_sha256: str,
        command_contract: Sequence[str],
        report_body: bytes,
        expected_target: Path,
        elapsed_seconds: float,
        process_exit_code: int,
        process_output_sha256: str,
        owner_checkout_unchanged: bool,
        workflow_binding_sha256: str | None = None,
    ) -> dict[str, object]:
        if not SAFE_DIGEST.fullmatch(executable_fingerprint):
            raise EvidenceError("security candidate fingerprint is invalid")
        if not re.fullmatch(r"[0-9a-f]{40,64}", candidate_commit):
            raise EvidenceError("security candidate commit is invalid")
        if (
            not isinstance(elapsed_seconds, (int, float))
            or isinstance(elapsed_seconds, bool)
            or not math.isfinite(float(elapsed_seconds))
            or float(elapsed_seconds) < 0
        ):
            raise EvidenceError("security elapsed time is invalid")
        if type(process_exit_code) is not int:
            raise EvidenceError("security process exit code is invalid")
        if type(owner_checkout_unchanged) is not bool:
            raise EvidenceError(
                "security Owner-checkout drift result is invalid"
            )
        _require_digest(process_output_sha256, "security process output digest")
        if workflow_binding_sha256 is not None:
            _require_digest(
                workflow_binding_sha256,
                "security workflow binding digest",
            )
        if not report_body or len(report_body) > MAX_LAUNCHGUARDIAN_REPORT_BYTES:
            raise EvidenceError("LaunchGuardian report size is outside its bound")
        report = _strict_json_bytes(report_body, "LaunchGuardian report")
        acceptance = launchguardian_report_acceptance(
            report, expected_target=expected_target
        )
        expected_target_text = str(expected_target.resolve(strict=True))
        command = _validate_launchguardian_command_contract(
            command_contract,
            executable_path=executable_path,
            expected_target=expected_target_text,
        )
        if process_exit_code != 0 and acceptance["accepted"] is True:
            acceptance = {
                **acceptance,
                "accepted": False,
                "workflow_outcome": "procedural_failure",
                "reason": (
                    "LaunchGuardian exited non-zero despite an apparently "
                    "accepted report"
                ),
            }
        report_sha256 = _digest_bytes(report_body)
        report_path = self.report_root / f"{report_sha256}.json"
        _write_bounded_evidence_bytes(report_path, report_body)
        identity = {
            "candidate_commit": candidate_commit,
            "command_contract": command,
            "executable_path": executable_path,
            "executable_sha256": _require_digest(
                executable_sha256, "LaunchGuardian executable digest"
            ),
            "executable_surface_sha256": _require_digest(
                executable_fingerprint, "security candidate fingerprint"
            ),
            "fingerprint_version": FINGERPRINT_VERSION,
            "report_sha256": report_sha256,
            "workflow_binding_sha256": workflow_binding_sha256,
        }
        record = {
            "schema_version": 1,
            "evidence_kind": "launchguardian_security_review",
            **identity,
            "acceptance": acceptance,
            "elapsed_seconds": float(elapsed_seconds),
            "owner_checkout_unchanged": owner_checkout_unchanged,
            "process_exit_code": process_exit_code,
            "process_output_sha256": process_output_sha256,
            "recorded_at": time.time(),
            "authenticated": False,
            "provenance_attested": False,
        }
        key = _digest_bytes(_canonical_json(record))
        record["record_key"] = key
        _atomic_json(self.record_root / f"{key}.json", record)
        return record

    def record_procedural_failure(
        self,
        *,
        candidate_commit: str,
        executable_fingerprint: str,
        stage: str,
        reason: str,
        executable_path: str | None,
        executable_sha256: str | None,
        process_exit_code: int | None,
        process_output_sha256: str,
        process_liveness: str,
        timed_out: bool,
        owner_checkout_unchanged: bool,
        workflow_binding_sha256: str,
    ) -> dict[str, object]:
        if not re.fullmatch(r"[0-9a-f]{40,64}", candidate_commit):
            raise EvidenceError("security candidate commit is invalid")
        _require_digest(
            executable_fingerprint, "security candidate fingerprint"
        )
        _require_digest(
            workflow_binding_sha256, "security workflow binding digest"
        )
        _require_digest(
            process_output_sha256, "security process output digest"
        )
        if stage not in SECURITY_PROCEDURAL_STAGES:
            raise EvidenceError("security procedural stage is invalid")
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or len(reason.encode("utf-8")) > 4096
        ):
            raise EvidenceError("security procedural reason is invalid")
        if type(owner_checkout_unchanged) is not bool:
            raise EvidenceError(
                "security Owner-checkout drift result is invalid"
            )
        if type(timed_out) is not bool:
            raise EvidenceError("security timeout result is invalid")
        if process_liveness not in {"absent", "not_started"}:
            raise EvidenceError("security process liveness result is invalid")
        if process_exit_code is not None and type(process_exit_code) is not int:
            raise EvidenceError("security process exit code is invalid")
        if executable_path is None:
            if (
                executable_sha256 is not None
                or process_exit_code is not None
                or process_liveness != "not_started"
                or timed_out
            ):
                raise EvidenceError(
                    "unstarted security process evidence is contradictory"
                )
        elif (
            not isinstance(executable_path, str)
            or not Path(executable_path).is_absolute()
            or not isinstance(executable_sha256, str)
            or not SAFE_DIGEST.fullmatch(executable_sha256)
            or process_liveness != "absent"
        ):
            raise EvidenceError(
                "started security process evidence is malformed"
            )
        if not _procedural_stage_consistent(
            stage=stage,
            executable_path=executable_path,
            process_liveness=process_liveness,
            timed_out=timed_out,
        ):
            raise EvidenceError(
                "security procedural stage contradicts process evidence"
            )
        record = {
            "schema_version": 1,
            "evidence_kind":
                "launchguardian_security_procedural_failure",
            "candidate_commit": candidate_commit,
            "executable_path": executable_path,
            "executable_sha256": executable_sha256,
            "executable_surface_sha256": executable_fingerprint,
            "fingerprint_version": FINGERPRINT_VERSION,
            "stage": stage,
            "reason": reason.strip(),
            "owner_checkout_unchanged": owner_checkout_unchanged,
            "process_exit_code": process_exit_code,
            "process_output_sha256": process_output_sha256,
            "process_liveness": process_liveness,
            "timed_out": timed_out,
            "recorded_at": time.time(),
            "authenticated": False,
            "provenance_attested": False,
            "workflow_binding_sha256": workflow_binding_sha256,
        }
        key = _digest_bytes(_canonical_json(record))
        record["record_key"] = key
        _atomic_json(self.record_root / f"{key}.json", record)
        return record

    def procedural_failure_acceptance(
        self,
        record: Mapping[str, object],
        *,
        executable_fingerprint: str,
        now: float | None = None,
    ) -> dict[str, object]:
        recorded_at = record.get("recorded_at")
        record_key = record.get("record_key")
        executable_path = record.get("executable_path")
        executable_sha256 = record.get("executable_sha256")
        process_exit_code = record.get("process_exit_code")
        process_liveness = record.get("process_liveness")
        timed_out = record.get("timed_out")
        if (
            set(record) != SECURITY_PROCEDURAL_RECORD_FIELDS
            or record.get("schema_version") != 1
            or record.get("evidence_kind")
            != "launchguardian_security_procedural_failure"
            or record.get("fingerprint_version") != FINGERPRINT_VERSION
            or record.get("executable_surface_sha256")
            != executable_fingerprint
            or record.get("stage") not in SECURITY_PROCEDURAL_STAGES
            or not isinstance(record.get("reason"), str)
            or not str(record.get("reason")).strip()
            or len(str(record.get("reason")).encode("utf-8")) > 4096
            or record.get("owner_checkout_unchanged") is not True
            or record.get("authenticated") is not False
            or record.get("provenance_attested") is not False
            or not isinstance(record.get("candidate_commit"), str)
            or not re.fullmatch(
                r"[0-9a-f]{40,64}", str(record.get("candidate_commit"))
            )
            or not isinstance(record.get("workflow_binding_sha256"), str)
            or not SAFE_DIGEST.fullmatch(
                str(record.get("workflow_binding_sha256"))
            )
            or not isinstance(record.get("process_output_sha256"), str)
            or not SAFE_DIGEST.fullmatch(
                str(record.get("process_output_sha256"))
            )
            or not isinstance(record_key, str)
            or not SAFE_DIGEST.fullmatch(record_key)
            or not isinstance(recorded_at, (int, float))
            or isinstance(recorded_at, bool)
            or not math.isfinite(float(recorded_at))
            or type(timed_out) is not bool
            or process_liveness not in {"absent", "not_started"}
            or (
                process_exit_code is not None
                and type(process_exit_code) is not int
            )
        ):
            return {
                "accepted": False,
                "reason": (
                    "security procedural evidence is absent, stale, or malformed"
                ),
            }
        if executable_path is None:
            if (
                executable_sha256 is not None
                or process_exit_code is not None
                or process_liveness != "not_started"
                or timed_out
            ):
                return {
                    "accepted": False,
                    "reason": "security procedural evidence is contradictory",
                }
        elif (
            not isinstance(executable_path, str)
            or not Path(executable_path).is_absolute()
            or not isinstance(executable_sha256, str)
            or not SAFE_DIGEST.fullmatch(executable_sha256)
            or process_liveness != "absent"
        ):
            return {
                "accepted": False,
                "reason": "security procedural process evidence is malformed",
            }
        if not _procedural_stage_consistent(
            stage=record.get("stage"),
            executable_path=executable_path,
            process_liveness=process_liveness,
            timed_out=timed_out,
        ):
            return {
                "accepted": False,
                "reason": (
                    "security procedural stage contradicts process evidence"
                ),
            }
        keyed_record = {
            key: value for key, value in record.items() if key != "record_key"
        }
        if _digest_bytes(_canonical_json(keyed_record)) != record_key:
            return {
                "accepted": False,
                "reason": "security review record key is mismatched",
            }
        clock = time.time() if now is None else now
        if (
            not isinstance(clock, (int, float))
            or isinstance(clock, bool)
            or not math.isfinite(float(clock))
            or float(recorded_at) > float(clock) + 2.0
            or float(clock) - float(recorded_at) > MAX_RESULT_AGE_SECONDS
        ):
            return {
                "accepted": False,
                "reason": "security review record is stale or future-dated",
            }
        return {
            "accepted": False,
            "workflow_outcome": "procedural_failure",
            "reason": str(record["reason"]),
            "stage": record["stage"],
            "authenticated": False,
            "provenance_attested": False,
        }

    def acceptance(
        self,
        record: Mapping[str, object],
        *,
        candidate_commit: str,
        executable_fingerprint: str,
        now: float | None = None,
    ) -> dict[str, object]:
        report_digest = record.get("report_sha256")
        process_exit_code = record.get("process_exit_code")
        executable_path = record.get("executable_path")
        executable_sha256 = record.get("executable_sha256")
        command_contract = record.get("command_contract")
        record_key = record.get("record_key")
        candidate_value = record.get("candidate_commit")
        elapsed_seconds = record.get("elapsed_seconds")
        recorded_at = record.get("recorded_at")
        workflow_binding = record.get("workflow_binding_sha256")
        if (
            set(record) != SECURITY_REVIEW_RECORD_FIELDS
            or record.get("schema_version") != 1
            or record.get("evidence_kind")
            != "launchguardian_security_review"
            or record.get("candidate_commit") != candidate_commit
            or record.get("executable_surface_sha256")
            != executable_fingerprint
            or record.get("fingerprint_version") != FINGERPRINT_VERSION
            or record.get("authenticated") is not False
            or record.get("provenance_attested") is not False
            or record.get("owner_checkout_unchanged") is not True
            or not isinstance(report_digest, str)
            or not SAFE_DIGEST.fullmatch(report_digest)
            or type(process_exit_code) is not int
            or not isinstance(executable_path, str)
            or not isinstance(executable_sha256, str)
            or not SAFE_DIGEST.fullmatch(executable_sha256)
            or not isinstance(command_contract, list)
            or not isinstance(record_key, str)
            or not SAFE_DIGEST.fullmatch(record_key)
            or not isinstance(candidate_value, str)
            or not re.fullmatch(r"[0-9a-f]{40,64}", candidate_value)
            or not isinstance(elapsed_seconds, (int, float))
            or isinstance(elapsed_seconds, bool)
            or not math.isfinite(float(elapsed_seconds))
            or float(elapsed_seconds) < 0
            or not isinstance(recorded_at, (int, float))
            or isinstance(recorded_at, bool)
            or not math.isfinite(float(recorded_at))
            or (
                workflow_binding is not None
                and (
                    not isinstance(workflow_binding, str)
                    or not SAFE_DIGEST.fullmatch(workflow_binding)
                )
            )
            or not isinstance(record.get("process_output_sha256"), str)
            or not SAFE_DIGEST.fullmatch(
                str(record.get("process_output_sha256"))
            )
        ):
            return {
                "accepted": False,
                "reason": "security review identity is absent, stale, or malformed",
            }
        keyed_record = {
            key: value for key, value in record.items() if key != "record_key"
        }
        if _digest_bytes(_canonical_json(keyed_record)) != record_key:
            return {
                "accepted": False,
                "reason": "security review record key is mismatched",
            }
        clock = time.time() if now is None else now
        if (
            not isinstance(clock, (int, float))
            or isinstance(clock, bool)
            or not math.isfinite(float(clock))
            or float(recorded_at) > float(clock) + 2.0
            or float(clock) - float(recorded_at) > MAX_RESULT_AGE_SECONDS
        ):
            return {
                "accepted": False,
                "reason": "security review record is stale or future-dated",
            }
        path = self.report_root / f"{report_digest}.json"
        try:
            body = _read_bounded_plain_bytes(
                path,
                maximum=MAX_LAUNCHGUARDIAN_REPORT_BYTES,
                label="LaunchGuardian report",
            )
            if (
                not body
                or _digest_bytes(body) != report_digest
            ):
                raise EvidenceError("security report bytes are absent or mismatched")
            report = _strict_json_bytes(body, "LaunchGuardian report")
            target = report.get("target")
            if not isinstance(target, str):
                raise EvidenceError("LaunchGuardian report target is invalid")
            _validate_launchguardian_command_contract(
                command_contract,
                executable_path=executable_path,
                expected_target=target,
            )
            acceptance = launchguardian_report_acceptance(
                report, expected_target=target
            )
            if process_exit_code != 0 and acceptance["accepted"] is True:
                acceptance = {
                    **acceptance,
                    "accepted": False,
                    "workflow_outcome": "procedural_failure",
                    "reason": (
                        "LaunchGuardian exited non-zero despite an apparently "
                        "accepted report"
                    ),
                }
        except (OSError, EvidenceError):
            return {
                "accepted": False,
                "reason": "security report bytes are absent, stale, or malformed",
            }
        if acceptance != record.get("acceptance"):
            return {
                "accepted": False,
                "reason": "security report summary differs from recorded evidence",
            }
        return {
            **acceptance,
            "authenticated": False,
            "provenance_attested": False,
        }

    def accepted_record(
        self,
        record_key: str,
        *,
        executable_fingerprint: str,
        workflow_binding_sha256: str,
    ) -> dict[str, object]:
        if not SAFE_DIGEST.fullmatch(record_key):
            return {
                "accepted": False,
                "reason": "security review record key is invalid",
            }
        if not SAFE_DIGEST.fullmatch(workflow_binding_sha256):
            return {
                "accepted": False,
                "reason": "security workflow binding digest is invalid",
            }
        try:
            body = _read_bounded_plain_bytes(
                self.record_root / f"{record_key}.json",
                maximum=MAX_RECORD_BYTES,
                label="security review record",
            )
            record = _strict_json_bytes(body, "security review record")
        except EvidenceError:
            return {
                "accepted": False,
                "reason": "security review record is absent or malformed",
            }
        if (
            record.get("evidence_kind")
            == "launchguardian_security_procedural_failure"
        ):
            if (
                record.get("workflow_binding_sha256")
                != workflow_binding_sha256
            ):
                return {
                    "accepted": False,
                    "reason": (
                        "security review belongs to another workflow admission"
                    ),
                }
            return self.procedural_failure_acceptance(
                record,
                executable_fingerprint=executable_fingerprint,
            )
        candidate_commit = record.get("candidate_commit")
        if not isinstance(candidate_commit, str):
            return {
                "accepted": False,
                "reason": "security review candidate commit is malformed",
            }
        if (
            record.get("workflow_binding_sha256")
            != workflow_binding_sha256
        ):
            return {
                "accepted": False,
                "reason": "security review belongs to another workflow admission",
            }
        return self.acceptance(
            record,
            candidate_commit=candidate_commit,
            executable_fingerprint=executable_fingerprint,
        )


def reusable_proof(
    record: Mapping[str, object],
    *,
    executable_fingerprint: str,
    command: Sequence[str],
    environment_sha256: str,
) -> bool:
    return (
        record.get("fingerprint_version") == FINGERPRINT_VERSION
        and
        record.get("scope") == "intermediate"
        and record.get("terminal_status") == "passed"
        and record.get("executable_surface_sha256") == executable_fingerprint
        and record.get("command") == list(command)
        and record.get("environment_sha256") == environment_sha256
    )


class ProofStore:
    """User-writable proof records; identity and reuse, never attestation."""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True) / "proofs"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(
        self,
        executable_fingerprint: str,
        command: Sequence[str],
        environment_sha256: str,
        scope: str,
    ) -> Path:
        if scope not in {"intermediate", "full_required_suite"}:
            raise EvidenceError("proof scope is invalid")
        key = _digest_bytes(
            _canonical_json(
                {
                    "executable_surface_sha256": _require_digest(
                        executable_fingerprint, "executable fingerprint"
                    ),
                    "fingerprint_version": FINGERPRINT_VERSION,
                    "command": list(command),
                    "environment_sha256": _require_digest(
                        environment_sha256, "environment fingerprint"
                    ),
                    "scope": scope,
                }
            )
        )
        return self.root / f"{key}.json"

    def record(
        self,
        *,
        executable_fingerprint: str,
        result: Mapping[str, object],
        scope: str,
    ) -> dict[str, object]:
        if scope not in {"intermediate", "full_required_suite"}:
            raise EvidenceError("proof scope is invalid")
        command = result.get("command")
        environment_sha256 = result.get("environment_sha256")
        if (
            not isinstance(command, list)
            or not all(isinstance(item, str) and item for item in command)
            or not isinstance(environment_sha256, str)
        ):
            raise EvidenceError("proof result lacks exact command/environment binding")
        record = {
            "schema_version": 2,
            "fingerprint_version": FINGERPRINT_VERSION,
            "scope": scope,
            "executable_surface_sha256": _require_digest(
                executable_fingerprint, "executable fingerprint"
            ),
            "command": command,
            "environment_sha256": _require_digest(
                environment_sha256, "environment fingerprint"
            ),
            "terminal_status": result.get("terminal_status"),
            "exit_code": result.get("exit_code"),
            "timed_out": result.get("timed_out"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "output_sha256": result.get("output_sha256"),
            "observed_at": time.time(),
            "authenticated": False,
        }
        path = self._path(
            executable_fingerprint, command, environment_sha256, scope
        )
        record["record_key"] = path.stem
        _atomic_json(path, record)
        return record

    def accepted_record(
        self,
        record_key: str,
        *,
        executable_fingerprint: str,
    ) -> dict[str, object]:
        if not SAFE_DIGEST.fullmatch(record_key):
            return {
                "accepted": False,
                "reason": "full-suite proof record key is invalid",
            }
        try:
            body = _read_bounded_plain_bytes(
                self.root / f"{record_key}.json",
                maximum=MAX_RECORD_BYTES,
                label="full-suite proof record",
            )
            record = _strict_json_bytes(body, "full-suite proof record")
        except EvidenceError:
            return {
                "accepted": False,
                "reason": "full-suite proof record is absent or malformed",
            }
        command = record.get("command")
        environment_sha256 = record.get("environment_sha256")
        if (
            record.get("record_key") != record_key
            or not isinstance(command, list)
            or not all(isinstance(item, str) and item for item in command)
            or not isinstance(environment_sha256, str)
        ):
            return {
                "accepted": False,
                "reason": "full-suite proof record identity is malformed",
            }
        expected_path = self._path(
            executable_fingerprint,
            command,
            environment_sha256,
            "full_required_suite",
        )
        if expected_path.stem != record_key:
            return {
                "accepted": False,
                "reason": "full-suite proof record key is mismatched",
            }
        return final_suite_acceptance(
            record,
            executable_fingerprint=executable_fingerprint,
        )

    def intermediate(
        self,
        *,
        candidate_state: Mapping[str, object],
        command: Sequence[str],
        environment_sha256: str,
    ) -> dict[str, object]:
        fingerprint = candidate_state.get("executable_surface_sha256")
        if (
            candidate_state.get("reuse_eligible") is not True
            or candidate_state.get("fingerprint_version") != FINGERPRINT_VERSION
            or not isinstance(fingerprint, str)
        ):
            return {
                "reusable": False,
                "reason": "candidate cleanliness or loadable-path proof is absent",
            }
        path = self._path(
            fingerprint, command, environment_sha256, "intermediate"
        )
        if not path.is_file():
            return {"reusable": False, "reason": "exact proof record is absent"}
        record = _read_json(path)
        return {
            "reusable": reusable_proof(
                record,
                executable_fingerprint=fingerprint,
                command=command,
                environment_sha256=environment_sha256,
            ),
            "record": record,
            "authenticated": False,
        }

    def final(
        self,
        *,
        executable_fingerprint: str,
        command: Sequence[str],
        environment_sha256: str,
    ) -> dict[str, object]:
        path = self._path(
            executable_fingerprint,
            command,
            environment_sha256,
            "full_required_suite",
        )
        if not path.is_file():
            return {
                "accepted": False,
                "reason": "final exact-fingerprint full-suite proof is absent",
            }
        return final_suite_acceptance(
            _read_json(path),
            executable_fingerprint=executable_fingerprint,
        )


def final_suite_acceptance(
    record: Mapping[str, object], *, executable_fingerprint: str
) -> dict[str, object]:
    command = record.get("command")
    exit_code = record.get("exit_code")
    accepted = (
        type(record.get("schema_version")) is int
        and record.get("schema_version") == 2
        and
        record.get("fingerprint_version") == FINGERPRINT_VERSION
        and
        record.get("scope") == "full_required_suite"
        and record.get("terminal_status") == "passed"
        and record.get("executable_surface_sha256") == executable_fingerprint
        and isinstance(command, list)
        and bool(command)
        and all(isinstance(item, str) and item for item in command)
        and isinstance(record.get("environment_sha256"), str)
        and bool(SAFE_DIGEST.fullmatch(str(record["environment_sha256"])))
        and isinstance(record.get("output_sha256"), str)
        and bool(SAFE_DIGEST.fullmatch(str(record["output_sha256"])))
        and type(exit_code) is int
        and exit_code == 0
        and record.get("timed_out") is False
        and record.get("authenticated") is False
    )
    return {
        "accepted": accepted,
        "authenticated": False,
        "provenance_attested": False,
        "reason": (
            "user-writable full-suite record is structurally accepted for the "
            "exact executable fingerprint; execution provenance is not attested"
            if accepted
            else "an exact structurally valid full-suite record is absent"
        ),
    }
