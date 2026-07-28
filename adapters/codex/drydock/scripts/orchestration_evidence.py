#!/usr/bin/env python3
"""Bounded local state, resource envelopes, and proof identity for Drydock."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
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
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator, Mapping, Sequence


PHASES = (
    "plan_peer",
    "mutation",
    "cross_review",
    "verification",
    "integration",
)
MAX_TERMINAL_BYTES = 64 * 1024
MAX_RECORD_BYTES = 128 * 1024
MAX_RESULT_AGE_SECONDS = 24 * 60 * 60
SAFE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
PEER_REVIEW_NAME = re.compile(
    r"^claude-architecture-review-round-[1-9][0-9]*\.json$"
)
INJECTION_NAMES = frozenset(
    {"conftest.py", "sitecustomize.py", "usercustomize.py"}
)
BYTECODE_SUFFIXES = frozenset({".pyc", ".pyo"})
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
        os.replace(temporary, path)
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


@contextlib.contextmanager
def _exclusive_record_lock(path: Path) -> Iterator[None]:
    lock = path.with_name(f".{path.name}.lock")
    identity = process_identity(os.getpid())
    if identity is None:
        raise EvidenceError("cannot establish process identity for state lock")
    payload = _canonical_json(
        {"process": identity, "created_at": time.time()}
    )
    try:
        with lock.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise EvidenceError(
            "orchestration state is locked; refusing a concurrent or stale update"
        ) from exc
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()


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


def _git(repo: Path, arguments: Sequence[str]) -> bytes:
    executable = shutil.which("git")
    if not executable:
        raise EvidenceError("Git executable is unavailable")
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith("GIT_"):
            environment.pop(key)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
        }
    )
    try:
        result = subprocess.run(
            [executable, *arguments],
            cwd=repo,
            capture_output=True,
            timeout=60,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceError(f"Git command could not run: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace")[-500:].strip()
        raise EvidenceError(f"Git command failed: {detail}")
    return result.stdout


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


def _valid_packet_json(path: Path) -> bool:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if path.name == "codex-final-verifier.json":
        return _valid_final_verifier(value)
    return _valid_peer_summary(value)


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
    tracked = [
        item.decode("utf-8", "surrogateescape")
        for item in _git(root, ["ls-files", "-z"]).split(b"\0")
        if item
    ]
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
    executable = hashlib.sha256()
    evidence = hashlib.sha256()
    tracked_bytecode: list[str] = []
    invalid_evidence: list[str] = []
    for name in sorted(tracked):
        path = root / PurePosixPath(name)
        metadata = os.stat(path, follow_symlinks=False)
        is_bytecode = (
            Path(name).suffix.casefold() in BYTECODE_SUFFIXES
            or "__pycache__" in PurePosixPath(name).parts
        )
        if is_bytecode:
            tracked_bytecode.append(name)
        evidence_path = _packet_evidence_path(name, packet_root)
        if evidence_path and (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or (path.suffix == ".json" and not _valid_packet_json(path))
        ):
            invalid_evidence.append(name)
            evidence_path = False
        if not (evidence_path and name == exclude_evidence_path):
            digest = evidence if evidence_path else executable
            digest.update(name.encode("utf-8", "surrogateescape"))
            digest.update(b"\0")
            if stat.S_ISLNK(metadata.st_mode):
                body = os.readlink(path).encode("utf-8", "surrogateescape")
                kind = b"symlink"
            elif stat.S_ISREG(metadata.st_mode):
                body = path.read_bytes()
                kind = b"file"
            else:
                raise EvidenceError(
                    f"tracked path has an unsupported type: {name}"
                )
            digest.update(kind)
            digest.update(b"\0")
            digest.update(str(metadata.st_mode & 0o777).encode("ascii"))
            digest.update(b"\0")
            digest.update(body)
            digest.update(b"\0")
    ignored_injection = sorted(
        name
        for name in ignored
        if PurePosixPath(name.rstrip("/")).name.casefold() in INJECTION_NAMES
        or PurePosixPath(name.rstrip("/")).suffix.casefold() == ".pth"
    )
    return {
        "head": _git(root, ["rev-parse", "HEAD"]).decode("ascii").strip(),
        "executable_surface_sha256": executable.hexdigest(),
        "packet_evidence_sha256": evidence.hexdigest(),
        "packet_evidence_excluded_path": exclude_evidence_path,
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
    archive = _git(repo, ["archive", "--format=tar", commit])
    with tempfile.TemporaryDirectory(prefix="drydock-proof-") as temporary:
        root = Path(temporary).resolve(strict=True)
        archive_path = root / ".archive.tar"
        archive_path.write_bytes(archive)
        with tarfile.open(archive_path, mode="r:") as bundle:
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
            bundle.extractall(root)
        archive_path.unlink()
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


def reusable_proof(
    record: Mapping[str, object],
    *,
    executable_fingerprint: str,
    command: Sequence[str],
    environment_sha256: str,
) -> bool:
    return (
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
    ) -> Path:
        key = _digest_bytes(
            _canonical_json(
                {
                    "executable_surface_sha256": _require_digest(
                        executable_fingerprint, "executable fingerprint"
                    ),
                    "command": list(command),
                    "environment_sha256": _require_digest(
                        environment_sha256, "environment fingerprint"
                    ),
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
            "schema_version": 1,
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
            executable_fingerprint, command, environment_sha256
        )
        _atomic_json(path, record)
        return record

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
            or not isinstance(fingerprint, str)
        ):
            return {
                "reusable": False,
                "reason": "candidate cleanliness or loadable-path proof is absent",
            }
        path = self._path(fingerprint, command, environment_sha256)
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
            executable_fingerprint, command, environment_sha256
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
    accepted = (
        record.get("scope") == "full_required_suite"
        and record.get("terminal_status") == "passed"
        and record.get("executable_surface_sha256") == executable_fingerprint
    )
    return {
        "accepted": accepted,
        "reason": (
            "full required suite passed on the exact executable fingerprint"
            if accepted
            else "final exact-fingerprint full-suite proof is absent"
        ),
    }
