#!/usr/bin/env python3
"""Serialized append-only event storage for Drydock delegation evidence."""

from __future__ import annotations

import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, TextIO

from delegation_contracts import (
    SCHEMA_VERSION,
    ContractError,
    canonical_json,
    digest_json,
    strict_json_loads,
    validate_digest,
    validate_identifier,
    validate_json_value,
    validate_storage_component,
    validate_timestamp,
)


MAX_LEDGER_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 32 * 1024
MAX_RECORDS = 10_000
DEFAULT_LOCK_TIMEOUT_S = 5.0
LOCK_RETRY_S = 0.025

EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "sequence",
        "event_id",
        "run_id",
        "event_type",
        "recorded_at",
        "delegation_id",
        "task_id",
        "status",
        "payload",
        "previous_record_digest",
        "record_digest",
    }
)

INTEGRITY_LIMITATIONS = (
    "records are unkeyed and user-writable",
    "writer authenticity is not established",
    "deletion of an unanchored suffix is not ruled out",
    "timestamps depend on the operating-system wall clock",
)


class LedgerError(RuntimeError):
    """The event stream could not be read or safely extended."""


_THREAD_LOCKS: Dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _thread_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _THREAD_LOCKS[key] = lock
        return lock


def _try_os_lock(stream: TextIO) -> bool:
    stream.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock_os(stream: TextIO) -> None:
    stream.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def exclusive_file_lock(
    path: Path, timeout_s: float = DEFAULT_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """Serialize threads and processes using a one-byte advisory file lock."""
    if not isinstance(timeout_s, (int, float)) or timeout_s <= 0:
        raise LedgerError("lock timeout must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock(path)
    if not thread_lock.acquire(timeout=timeout_s):
        raise LedgerError("timed out acquiring the in-process ledger lock")
    stream: Optional[TextIO] = None
    locked = False
    try:
        stream = path.open("a+b")
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic() + timeout_s
        while True:
            if _try_os_lock(stream):
                locked = True
                break
            if time.monotonic() >= deadline:
                raise LedgerError("timed out acquiring the process ledger lock")
            time.sleep(LOCK_RETRY_S)
        yield
    finally:
        if stream is not None:
            try:
                if locked:
                    _unlock_os(stream)
            finally:
                stream.close()
        thread_lock.release()


def _integrity_report(
    *,
    valid: bool,
    record_count: int,
    last_record_digest: Optional[str],
    corruption: Optional[Mapping[str, object]],
) -> Dict[str, object]:
    return {
        "valid": valid,
        "record_count": record_count,
        "last_record_digest": last_record_digest,
        "corruption": dict(corruption) if corruption is not None else None,
        "authenticity": "not_established",
        "suffix_completeness": "not_established",
        "limitations": list(INTEGRITY_LIMITATIONS),
    }


def _validate_event(
    value: object,
    *,
    expected_run_id: str,
    expected_sequence: int,
    expected_previous_digest: Optional[str],
    seen_event_ids: set,
) -> Mapping[str, object]:
    if not isinstance(value, dict) or set(value) != EVENT_FIELDS:
        raise LedgerError("event fields do not match the schema")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != SCHEMA_VERSION
    ):
        raise LedgerError("unsupported event schema")
    sequence = value["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise LedgerError("event sequence must be an integer")
    if sequence != expected_sequence:
        raise LedgerError(
            "event sequence {} does not equal expected {}".format(
                sequence, expected_sequence
            )
        )
    run_id = validate_storage_component(value["run_id"], "run_id")
    if run_id != expected_run_id:
        raise LedgerError("event run_id does not match the ledger")
    event_id = validate_identifier(value["event_id"], "event_id")
    if event_id in seen_event_ids:
        raise LedgerError("duplicate event_id")
    seen_event_ids.add(event_id)
    validate_identifier(value["event_type"], "event_type")
    validate_identifier(value["status"], "status")
    validate_timestamp(value["recorded_at"], "recorded_at")
    for field in ("delegation_id", "task_id"):
        if value[field] is not None:
            validate_identifier(value[field], field)
    validate_json_value(value["payload"])
    if value["previous_record_digest"] != expected_previous_digest:
        raise LedgerError("previous_record_digest does not match the chain")
    if expected_previous_digest is not None:
        validate_digest(expected_previous_digest, "previous_record_digest")
    record_digest = validate_digest(value["record_digest"], "record_digest")
    without_digest = dict(value)
    del without_digest["record_digest"]
    if digest_json(without_digest) != record_digest:
        raise LedgerError("record_digest does not match the event bytes")
    return value


def _read_records_unlocked(
    path: Path, run_id: str
) -> tuple[List[Mapping[str, object]], Dict[str, object]]:
    if not path.exists():
        return [], _integrity_report(
            valid=True,
            record_count=0,
            last_record_digest=None,
            corruption=None,
        )
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise LedgerError("could not stat event ledger: {}".format(exc)) from exc
    if size > MAX_LEDGER_BYTES:
        return [], _integrity_report(
            valid=False,
            record_count=0,
            last_record_digest=None,
            corruption={"line": None, "reason": "ledger exceeds the byte bound"},
        )

    records: List[Mapping[str, object]] = []
    previous_digest: Optional[str] = None
    seen_event_ids: set = set()
    try:
        with path.open("rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                if line_number > MAX_RECORDS:
                    return records, _integrity_report(
                        valid=False,
                        record_count=len(records),
                        last_record_digest=previous_digest,
                        corruption={
                            "line": line_number,
                            "reason": "ledger exceeds the record bound",
                        },
                    )
                if len(raw_line) > MAX_LINE_BYTES:
                    return records, _integrity_report(
                        valid=False,
                        record_count=len(records),
                        last_record_digest=previous_digest,
                        corruption={
                            "line": line_number,
                            "reason": "event line exceeds the byte bound",
                        },
                    )
                if not raw_line.endswith(b"\n"):
                    return records, _integrity_report(
                        valid=False,
                        record_count=len(records),
                        last_record_digest=previous_digest,
                        corruption={
                            "line": line_number,
                            "reason": "event line is not newline-terminated",
                        },
                    )
                try:
                    text = raw_line[:-1].decode("utf-8")
                    parsed = strict_json_loads(text)
                    event = _validate_event(
                        parsed,
                        expected_run_id=run_id,
                        expected_sequence=line_number,
                        expected_previous_digest=previous_digest,
                        seen_event_ids=seen_event_ids,
                    )
                except (UnicodeDecodeError, ContractError, LedgerError) as exc:
                    return records, _integrity_report(
                        valid=False,
                        record_count=len(records),
                        last_record_digest=previous_digest,
                        corruption={"line": line_number, "reason": str(exc)},
                    )
                records.append(event)
                previous_digest = event["record_digest"]  # type: ignore[assignment]
    except OSError as exc:
        raise LedgerError("could not read event ledger: {}".format(exc)) from exc

    return records, _integrity_report(
        valid=True,
        record_count=len(records),
        last_record_digest=previous_digest,
        corruption=None,
    )


class RunLedger:
    """One bounded event stream for a single Drydock run."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.run_id = validate_storage_component(run_id, "run_id")
        self.directory = Path(root) / self.run_id
        self.path = self.directory / "events.jsonl"
        self.lock_path = self.directory / ".events.lock"

    def verify(self) -> Dict[str, object]:
        with exclusive_file_lock(self.lock_path):
            _, report = _read_records_unlocked(self.path, self.run_id)
        return report

    def read_records(self) -> List[Mapping[str, object]]:
        with exclusive_file_lock(self.lock_path):
            records, report = _read_records_unlocked(self.path, self.run_id)
        if not report["valid"]:
            corruption = report["corruption"]
            raise LedgerError("event ledger is corrupt: {}".format(corruption))
        return records

    def append(
        self,
        *,
        event_type: str,
        status: str,
        payload: Mapping[str, object],
        delegation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        event_id: Optional[str] = None,
        recorded_at: Optional[str] = None,
    ) -> Mapping[str, object]:
        validate_identifier(event_type, "event_type")
        validate_identifier(status, "status")
        if not isinstance(payload, dict):
            raise ContractError("event payload must be an object")
        validate_json_value(payload)
        if delegation_id is not None:
            validate_identifier(delegation_id, "delegation_id")
        if task_id is not None:
            validate_identifier(task_id, "task_id")
        selected_event_id = event_id or str(uuid.uuid4())
        validate_identifier(selected_event_id, "event_id")
        selected_time = recorded_at or utc_now()
        validate_timestamp(selected_time, "recorded_at")

        self.directory.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(self.lock_path):
            records, report = _read_records_unlocked(self.path, self.run_id)
            if not report["valid"]:
                raise LedgerError(
                    "existing event ledger is corrupt: {}".format(
                        report["corruption"]
                    )
                )
            if len(records) >= MAX_RECORDS:
                raise LedgerError("event ledger reached the record bound")
            if any(record["event_id"] == selected_event_id for record in records):
                raise LedgerError("event_id already exists")
            previous_digest = report["last_record_digest"]
            event: Dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "sequence": len(records) + 1,
                "event_id": selected_event_id,
                "run_id": self.run_id,
                "event_type": event_type,
                "recorded_at": selected_time,
                "delegation_id": delegation_id,
                "task_id": task_id,
                "status": status,
                "payload": dict(payload),
                "previous_record_digest": previous_digest,
            }
            event["record_digest"] = digest_json(event)
            raw = canonical_json(event).encode("utf-8") + b"\n"
            if len(raw) > MAX_LINE_BYTES:
                raise ContractError("event line exceeds the byte bound")
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size + len(raw) > MAX_LEDGER_BYTES:
                raise LedgerError("event ledger would exceed the byte bound")
            try:
                with self.path.open("ab") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise LedgerError(
                    "could not append event ledger: {}".format(exc)
                ) from exc
        return event
