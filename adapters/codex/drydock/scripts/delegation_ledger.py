#!/usr/bin/env python3
"""Schema-v2 append-only delegation ledger and explicit torn-tail repair."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Dict, Iterator, List, Mapping, Optional, Sequence

from . import delegation_contracts as contracts


MAX_LEDGER_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 32 * 1024
MAX_RECORDS = 10_000
DEFAULT_LOCK_TIMEOUT_S = 30.0
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
        "runtime_status",
        "payload",
        "previous_record_digest",
        "record_digest",
    }
)
REPAIR_INTENT_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "created_at",
        "before_digest",
        "valid_prefix_byte_count",
        "valid_prefix_record_count",
        "last_valid_record_digest",
        "discarded_tail_digest",
        "discarded_tail_byte_count",
        "structural_classification",
        "extractable_sequence",
        "candidate_repaired_digest",
        "quarantine_ref",
        "quarantine_digest",
        "intent_digest",
    }
)
REPAIR_CLASSIFICATIONS = frozenset(
    {"truncated_json", "unterminated_string", "truncated_utf8_codepoint"}
)
INTEGRITY_LIMITATIONS = (
    "records are unkeyed and user-writable",
    "writer authenticity is not established",
    "deletion of an unanchored suffix is not ruled out",
    "timestamps depend on the operating-system wall clock",
)


class LedgerError(RuntimeError):
    """The event stream could not be read or safely extended."""


class RepairInterrupted(LedgerError):
    """Deterministic test-only interruption at a durable repair boundary."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _try_os_lock(stream: BinaryIO) -> bool:
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


def _unlock_os(stream: BinaryIO) -> None:
    stream.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _validate_timeout(timeout_s: float) -> float:
    if (
        isinstance(timeout_s, bool)
        or not isinstance(timeout_s, (int, float))
        or not 0 < timeout_s <= DEFAULT_LOCK_TIMEOUT_S
    ):
        raise LedgerError(
            "lock timeout must be positive and no greater than 30 seconds"
        )
    return float(timeout_s)


def _acquire_stream_lock(stream: BinaryIO, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        if _try_os_lock(stream):
            return
        if time.monotonic() >= deadline:
            raise LedgerError("timed out acquiring the single-writer store lock")
        time.sleep(LOCK_RETRY_S)


@contextmanager
def exclusive_file_lock(
    path: Path, timeout_s: float = DEFAULT_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """Create and hold the single-writer cross-process lock.

    The store supports one logical writer. This lock only serializes accidental
    concurrent physical writers and uses a fixed maximum 30-second wait.
    """
    selected_timeout = _validate_timeout(timeout_s)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream: Optional[BinaryIO] = None
    locked = False
    try:
        stream = path.open("a+b")
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        _acquire_stream_lock(stream, selected_timeout)
        locked = True
        yield
    finally:
        if stream is not None:
            try:
                if locked:
                    _unlock_os(stream)
            finally:
                stream.close()


@contextmanager
def read_only_file_lock(
    path: Path, timeout_s: float = DEFAULT_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """Lock an existing store without creating any filesystem entry."""
    selected_timeout = _validate_timeout(timeout_s)
    if not path.exists():
        yield
        return
    stream: Optional[BinaryIO] = None
    locked = False
    try:
        # Windows byte-range locking requires a writable handle; this mode does
        # not write or change file metadata/content.
        mode = "r+b" if os.name == "nt" else "rb"
        try:
            stream = path.open(mode)
        except FileNotFoundError:
            yield
            return
        _acquire_stream_lock(stream, selected_timeout)
        locked = True
        yield
    finally:
        if stream is not None:
            try:
                if locked:
                    _unlock_os(stream)
            finally:
                stream.close()


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
        "corruption": (
            contracts.detached_json_copy(dict(corruption))
            if corruption is not None
            else None
        ),
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
        or value["schema_version"] != contracts.SCHEMA_VERSION
    ):
        raise LedgerError("unsupported event schema; v2 required")
    sequence = value["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise LedgerError("event sequence must be an integer")
    if sequence != expected_sequence:
        raise LedgerError(
            "event sequence {} does not equal expected {}".format(
                sequence, expected_sequence
            )
        )
    run_id = contracts.validate_storage_component(value["run_id"], "run_id")
    if run_id != expected_run_id:
        raise LedgerError("event run_id does not match the ledger")
    event_id = contracts.validate_identifier(value["event_id"], "event_id")
    if event_id in seen_event_ids:
        raise LedgerError("duplicate event_id")
    seen_event_ids.add(event_id)
    contracts.validate_identifier(value["event_type"], "event_type")
    contracts.validate_identifier(value["runtime_status"], "runtime_status")
    contracts.validate_timestamp(value["recorded_at"], "recorded_at")
    for field in ("delegation_id", "task_id"):
        if value[field] is not None:
            contracts.validate_identifier(value[field], field)
    contracts.validate_json_value(value["payload"])
    if value["previous_record_digest"] != expected_previous_digest:
        raise LedgerError("previous_record_digest does not match the chain")
    if expected_previous_digest is not None:
        contracts.validate_digest(
            expected_previous_digest, "previous_record_digest"
        )
    record_digest = contracts.validate_digest(
        value["record_digest"], "record_digest"
    )
    without_digest = dict(value)
    del without_digest["record_digest"]
    if contracts.digest_json(without_digest) != record_digest:
        raise LedgerError("record_digest does not match the event content")
    return value


def _read_records_bytes(
    data: bytes, run_id: str
) -> tuple[List[Mapping[str, object]], Dict[str, object]]:
    if len(data) > MAX_LEDGER_BYTES:
        return [], _integrity_report(
            valid=False,
            record_count=0,
            last_record_digest=None,
            corruption={"line": None, "reason": "ledger exceeds the byte bound"},
        )
    records: List[Mapping[str, object]] = []
    previous_digest: Optional[str] = None
    seen_event_ids: set = set()
    for line_number, raw_line in enumerate(
        data.splitlines(keepends=True), start=1
    ):
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
            parsed = contracts.strict_json_loads(raw_line[:-1].decode("utf-8"))
            event = _validate_event(
                parsed,
                expected_run_id=run_id,
                expected_sequence=line_number,
                expected_previous_digest=previous_digest,
                seen_event_ids=seen_event_ids,
            )
        except (
            UnicodeDecodeError,
            contracts.ContractError,
            LedgerError,
        ) as exc:
            return records, _integrity_report(
                valid=False,
                record_count=len(records),
                last_record_digest=previous_digest,
                corruption={"line": line_number, "reason": str(exc)},
            )
        records.append(event)
        previous_digest = event["record_digest"]  # type: ignore[assignment]
    return records, _integrity_report(
        valid=True,
        record_count=len(records),
        last_record_digest=previous_digest,
        corruption=None,
    )


def _read_records_unlocked(
    path: Path, run_id: str
) -> tuple[List[Mapping[str, object]], Dict[str, object]]:
    if not path.exists():
        return _read_records_bytes(b"", run_id)
    try:
        return _read_records_bytes(path.read_bytes(), run_id)
    except OSError as exc:
        raise LedgerError("could not read event ledger: {}".format(exc)) from exc


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(str(path), flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _intent_digest(value: Mapping[str, object]) -> str:
    unsigned = dict(value)
    unsigned.pop("intent_digest", None)
    return contracts.digest_json(unsigned)


def _validate_repair_intent(value: object, expected_run_id: str) -> Dict[str, object]:
    if not isinstance(value, dict) or set(value) != REPAIR_INTENT_FIELDS:
        raise LedgerError("repair intent fields do not match schema")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != contracts.SCHEMA_VERSION
    ):
        raise LedgerError("unsupported repair intent schema; v2 required")
    run_id = contracts.validate_storage_component(value["run_id"], "run_id")
    if run_id != expected_run_id:
        raise LedgerError("repair intent run_id does not match ledger")
    contracts.validate_timestamp(value["created_at"], "created_at")
    for field in (
        "before_digest",
        "discarded_tail_digest",
        "candidate_repaired_digest",
        "intent_digest",
    ):
        contracts.validate_digest(value[field], field)
    for field in (
        "valid_prefix_byte_count",
        "valid_prefix_record_count",
        "discarded_tail_byte_count",
    ):
        number = value[field]
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise LedgerError("{} must be a non-negative integer".format(field))
    if value["valid_prefix_byte_count"] > MAX_LEDGER_BYTES:
        raise LedgerError("repair intent prefix exceeds ledger capacity")
    if value["valid_prefix_record_count"] > MAX_RECORDS:
        raise LedgerError("repair intent record count exceeds capacity")
    if value["discarded_tail_byte_count"] <= 0:
        raise LedgerError("repair intent must discard a non-empty tail")
    if value["structural_classification"] not in REPAIR_CLASSIFICATIONS:
        raise LedgerError("repair intent classification is unsupported")
    sequence = value["extractable_sequence"]
    if sequence is not None and (
        isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence <= 0
        or sequence > MAX_RECORDS
    ):
        raise LedgerError("repair intent extractable_sequence is invalid")
    if value["last_valid_record_digest"] is not None:
        contracts.validate_digest(
            value["last_valid_record_digest"], "last_valid_record_digest"
        )
    quarantine_ref = value["quarantine_ref"]
    quarantine_digest = value["quarantine_digest"]
    if (quarantine_ref is None) != (quarantine_digest is None):
        raise LedgerError("repair quarantine metadata is incomplete")
    if quarantine_ref is not None:
        contracts.validate_reference(quarantine_ref, "quarantine_ref")
        contracts.validate_digest(quarantine_digest, "quarantine_digest")
    if _intent_digest(value) != value["intent_digest"]:
        raise LedgerError("repair intent self-digest does not match")
    return dict(value)


def _read_intent(path: Path, run_id: str) -> Dict[str, object]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LedgerError("could not read repair intent: {}".format(exc)) from exc
    if not raw.endswith(b"\n"):
        raise LedgerError("repair intent is not newline-terminated")
    try:
        value = contracts.strict_json_loads(raw[:-1].decode("utf-8"))
        return _validate_repair_intent(value, run_id)
    except (UnicodeDecodeError, contracts.ContractError, LedgerError) as exc:
        raise LedgerError(
            "malformed repair intent {}: {}".format(path.name, exc)
        ) from exc


def _classify_torn_tail(
    data: bytes, run_id: str
) -> tuple[bytes, bytes, str, Optional[int], List[Mapping[str, object]]]:
    if not data or data.endswith(b"\n"):
        raise LedgerError(
            "repair requires a non-empty final non-newline torn tail"
        )
    prefix_end = data.rfind(b"\n") + 1
    prefix = data[:prefix_end]
    tail = data[prefix_end:]
    prefix_records, prefix_report = _read_records_bytes(prefix, run_id)
    if not prefix_report["valid"]:
        raise LedgerError(
            "repair refused because the valid prefix is corrupt: {}".format(
                prefix_report["corruption"]
            )
        )
    if len(tail) > MAX_LINE_BYTES:
        raise LedgerError("repair refused because the torn tail exceeds line capacity")

    extractable = re.findall(rb'"sequence"\s*:\s*(\d+)', tail)
    if len(extractable) > 1:
        raise LedgerError("repair refused because tail sequence is ambiguous")
    sequence = int(extractable[0]) if extractable else None
    expected_sequence = len(prefix_records) + 1
    if sequence is not None and sequence != expected_sequence:
        raise LedgerError(
            "repair refused because extractable sequence is not the next record"
        )

    try:
        text = tail.decode("utf-8")
    except UnicodeDecodeError as exc:
        if exc.end != len(tail) or exc.reason != "unexpected end of data":
            raise LedgerError(
                "repair refused because tail UTF-8 corruption is not terminal"
            ) from exc
        return (
            prefix,
            tail,
            "truncated_utf8_codepoint",
            sequence,
            prefix_records,
        )

    if re.search(r"(?<![A-Za-z0-9_])(?:NaN|-?Infinity)(?![A-Za-z0-9_])", text):
        raise LedgerError("repair refused because tail contains non-finite JSON")
    decoder = json.JSONDecoder()
    try:
        _, end = decoder.raw_decode(text)
    except json.JSONDecodeError as exc:
        if exc.msg == "Unterminated string starting at":
            classification = "unterminated_string"
        elif exc.pos >= max(0, len(text) - 1):
            classification = "truncated_json"
        else:
            raise LedgerError(
                "repair refused because tail corruption is not terminal/structural"
            ) from exc
    else:
        if not text[end:].strip():
            raise LedgerError(
                "repair refused because a complete record missing only newline is ambiguous"
            )
        raise LedgerError("repair refused because tail contains trailing corruption")
    return prefix, tail, classification, sequence, prefix_records


def _fault(step: str, selected: Optional[str]) -> None:
    if selected == step:
        raise RepairInterrupted("fault injected after {}".format(step))


class RunLedger:
    """One bounded, single-logical-writer event stream for one Drydock run."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.run_id = contracts.validate_storage_component(run_id, "run_id")
        self.directory = Path(root) / self.run_id
        self.path = self.directory / "events.jsonl"
        self.lock_path = self.directory / ".events.lock"
        self.intent_directory = self.directory / "repair-intents"
        self.quarantine_directory = self.directory / "repair-quarantine"

    def verify(self) -> Dict[str, object]:
        with read_only_file_lock(self.lock_path):
            _, report = _read_records_unlocked(self.path, self.run_id)
        return report

    def read_records(self) -> List[Mapping[str, object]]:
        with read_only_file_lock(self.lock_path):
            records, report = _read_records_unlocked(self.path, self.run_id)
        if not report["valid"]:
            raise LedgerError(
                "event ledger is corrupt: {}".format(report["corruption"])
            )
        return records

    def append(
        self,
        *,
        event_type: str,
        runtime_status: str,
        payload: Mapping[str, object],
        delegation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        event_id: Optional[str] = None,
        recorded_at: Optional[str] = None,
    ) -> Mapping[str, object]:
        contracts.validate_identifier(event_type, "event_type")
        contracts.validate_identifier(runtime_status, "runtime_status")
        if not isinstance(payload, dict):
            raise contracts.ContractError("event payload must be an object")
        detached_payload = contracts.detached_json_copy(payload)
        if not isinstance(detached_payload, dict):
            raise contracts.ContractError("event payload must remain an object")
        if delegation_id is not None:
            contracts.validate_identifier(delegation_id, "delegation_id")
        if task_id is not None:
            contracts.validate_identifier(task_id, "task_id")
        selected_event_id = event_id or str(uuid.uuid4())
        contracts.validate_identifier(selected_event_id, "event_id")
        selected_time = recorded_at or utc_now()
        contracts.validate_timestamp(selected_time, "recorded_at")

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
            event: Dict[str, object] = {
                "schema_version": contracts.SCHEMA_VERSION,
                "sequence": len(records) + 1,
                "event_id": selected_event_id,
                "run_id": self.run_id,
                "event_type": event_type,
                "recorded_at": selected_time,
                "delegation_id": delegation_id,
                "task_id": task_id,
                "runtime_status": runtime_status,
                "payload": detached_payload,
                "previous_record_digest": report["last_record_digest"],
            }
            event["record_digest"] = contracts.digest_json(event)
            raw = contracts.canonical_json(event).encode("utf-8") + b"\n"
            if len(raw) > MAX_LINE_BYTES:
                raise contracts.ContractError(
                    "event line exceeds the byte bound"
                )
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
        return contracts.detached_json_copy(event)  # type: ignore[return-value]

    def repair_torn_tail(
        self,
        *,
        expected_digest: str,
        quarantine: bool = False,
        _fault_after: Optional[str] = None,
    ) -> Mapping[str, object]:
        """Explicitly discard one classified final torn tail.

        ``_fault_after`` is a deterministic test seam. Operator callers should
        omit it. Repair is never called by append/read/verify.
        """
        contracts.validate_digest(expected_digest, "expected_digest")
        if not isinstance(quarantine, bool):
            raise LedgerError("quarantine selection must be boolean")
        allowed_faults = {
            None,
            "pre_intent",
            "post_intent",
            "post_quarantine",
            "post_candidate",
            "post_replace",
        }
        if _fault_after not in allowed_faults:
            raise LedgerError("unsupported repair fault step")

        self.directory.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(self.lock_path):
            try:
                data = self.path.read_bytes()
            except FileNotFoundError as exc:
                raise LedgerError("repair requires an existing ledger") from exc
            except OSError as exc:
                raise LedgerError("could not read ledger for repair: {}".format(exc)) from exc
            current_digest = contracts.digest_bytes(data)

            intents: List[Dict[str, object]] = []
            if self.intent_directory.exists():
                try:
                    intent_paths = sorted(self.intent_directory.glob("*.json"))
                except OSError as exc:
                    raise LedgerError(
                        "could not enumerate repair intents: {}".format(exc)
                    ) from exc
                for intent_path in intent_paths:
                    intent = _read_intent(intent_path, self.run_id)
                    intents.append(intent)
                    prefix_length = intent["valid_prefix_byte_count"]
                    candidate_digest = intent["candidate_repaired_digest"]
                    if current_digest not in (
                        intent["before_digest"],
                        candidate_digest,
                    ):
                        if (
                            not isinstance(prefix_length, int)
                            or len(data) < prefix_length
                            or contracts.digest_bytes(data[:prefix_length])
                            != candidate_digest
                        ):
                            raise LedgerError(
                                "existing repair intent conflicts with current ledger"
                            )

            matching = next(
                (
                    intent
                    for intent in intents
                    if intent["before_digest"] == expected_digest
                ),
                None,
            )
            if current_digest != expected_digest:
                if (
                    matching is not None
                    and current_digest == matching["candidate_repaired_digest"]
                ):
                    _fsync_directory(self.directory)
                    return {
                        "status": "completed_replay",
                        "before_digest": expected_digest,
                        "current_digest": current_digest,
                        "intent_digest": matching["intent_digest"],
                    }
                raise LedgerError(
                    "stale repair intent: current ledger digest does not match expected"
                )

            prefix, tail, classification, sequence, prefix_records = (
                _classify_torn_tail(data, self.run_id)
            )
            before_hex = expected_digest.split(":", 1)[1]
            quarantine_ref = (
                "repair-quarantine/{}.bin".format(before_hex)
                if quarantine
                else None
            )
            proposed: Dict[str, object] = {
                "schema_version": contracts.SCHEMA_VERSION,
                "run_id": self.run_id,
                "created_at": (
                    matching["created_at"] if matching is not None else utc_now()
                ),
                "before_digest": expected_digest,
                "valid_prefix_byte_count": len(prefix),
                "valid_prefix_record_count": len(prefix_records),
                "last_valid_record_digest": (
                    prefix_records[-1]["record_digest"]
                    if prefix_records
                    else None
                ),
                "discarded_tail_digest": contracts.digest_bytes(tail),
                "discarded_tail_byte_count": len(tail),
                "structural_classification": classification,
                "extractable_sequence": sequence,
                "candidate_repaired_digest": contracts.digest_bytes(prefix),
                "quarantine_ref": quarantine_ref,
                "quarantine_digest": (
                    contracts.digest_bytes(tail) if quarantine else None
                ),
            }
            proposed["intent_digest"] = _intent_digest(proposed)
            if matching is not None and matching != proposed:
                raise LedgerError(
                    "existing repair intent conflicts with requested repair"
                )

            _fault("pre_intent", _fault_after)
            intent_path = self.intent_directory / "{}.json".format(before_hex)
            if matching is None:
                self.intent_directory.mkdir(parents=True, exist_ok=True)
                raw_intent = (
                    contracts.canonical_json(proposed).encode("utf-8") + b"\n"
                )
                try:
                    with intent_path.open("xb") as stream:
                        stream.write(raw_intent)
                        stream.flush()
                        os.fsync(stream.fileno())
                    _fsync_directory(self.intent_directory)
                    _fsync_directory(self.directory)
                except FileExistsError as exc:
                    raise LedgerError(
                        "conflicting repair intent appeared concurrently"
                    ) from exc
                except OSError as exc:
                    raise LedgerError(
                        "could not persist repair intent: {}".format(exc)
                    ) from exc
                matching = proposed
            _fault("post_intent", _fault_after)

            if quarantine_ref is not None:
                self.quarantine_directory.mkdir(parents=True, exist_ok=True)
                quarantine_path = self.directory / quarantine_ref
                if quarantine_path.exists():
                    try:
                        existing = quarantine_path.read_bytes()
                    except OSError as exc:
                        raise LedgerError(
                            "could not read repair quarantine: {}".format(exc)
                        ) from exc
                    if existing != tail:
                        raise LedgerError(
                            "existing repair quarantine conflicts with intent"
                        )
                else:
                    try:
                        with quarantine_path.open("xb") as stream:
                            stream.write(tail)
                            stream.flush()
                            os.fsync(stream.fileno())
                        _fsync_directory(self.quarantine_directory)
                    except OSError as exc:
                        raise LedgerError(
                            "could not persist repair quarantine: {}".format(exc)
                        ) from exc
                _fault("post_quarantine", _fault_after)

            candidate_path = self.directory / (
                "events.repair-{}.candidate".format(before_hex)
            )
            if candidate_path.exists():
                try:
                    candidate_bytes = candidate_path.read_bytes()
                except OSError as exc:
                    raise LedgerError(
                        "could not read repair candidate: {}".format(exc)
                    ) from exc
                if candidate_bytes != prefix:
                    raise LedgerError(
                        "existing repair candidate conflicts with intent"
                    )
            else:
                try:
                    with candidate_path.open("xb") as stream:
                        stream.write(prefix)
                        stream.flush()
                        os.fsync(stream.fileno())
                    _fsync_directory(self.directory)
                except OSError as exc:
                    raise LedgerError(
                        "could not persist repair candidate: {}".format(exc)
                    ) from exc
            _fault("post_candidate", _fault_after)
            try:
                os.replace(str(candidate_path), str(self.path))
            except OSError as exc:
                raise LedgerError(
                    "could not atomically replace repaired ledger: {}".format(exc)
                ) from exc
            _fault("post_replace", _fault_after)
            _fsync_directory(self.directory)
            return {
                "status": "repaired",
                "before_digest": expected_digest,
                "current_digest": proposed["candidate_repaired_digest"],
                "discarded_tail_byte_count": len(tail),
                "structural_classification": classification,
                "intent_digest": proposed["intent_digest"],
                "quarantine_ref": quarantine_ref,
            }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--run-id", required=True)
    repair = subparsers.add_parser("repair-torn-tail")
    repair.add_argument("--root", type=Path, required=True)
    repair.add_argument("--run-id", required=True)
    repair.add_argument("--expected-digest", required=True)
    repair.add_argument("--quarantine", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    ledger = RunLedger(args.root, args.run_id)
    if args.command == "verify":
        value = ledger.verify()
    else:
        value = ledger.repair_torn_tail(
            expected_digest=args.expected_digest,
            quarantine=args.quarantine,
        )
    print(json.dumps(value, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
