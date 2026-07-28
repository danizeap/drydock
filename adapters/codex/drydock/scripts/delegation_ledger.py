#!/usr/bin/env python3
"""Schema-v2 append-only delegation ledger and explicit torn-tail repair."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
import types
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Dict, Iterator, List, Mapping, Optional, Sequence

if __package__:
    from . import delegation_contracts as contracts
else:
    # Direct execution has no package context. Build a private qualified
    # namespace pinned to this exact plugin's root so an unrelated ambient
    # ``scripts`` or ``delegation_contracts`` module cannot satisfy the import.
    _SCRIPT_DIRECTORY = Path(__file__).resolve().parent
    _PLUGIN_DIRECTORY = _SCRIPT_DIRECTORY.parent
    _BOOTSTRAP_ROOT = "_drydock_direct_plugin"
    _BOOTSTRAP_SCRIPTS = _BOOTSTRAP_ROOT + ".scripts"

    root_package = types.ModuleType(_BOOTSTRAP_ROOT)
    root_package.__path__ = [str(_PLUGIN_DIRECTORY)]  # type: ignore[attr-defined]
    root_package.__package__ = _BOOTSTRAP_ROOT
    scripts_package = types.ModuleType(_BOOTSTRAP_SCRIPTS)
    scripts_package.__path__ = [str(_SCRIPT_DIRECTORY)]  # type: ignore[attr-defined]
    scripts_package.__package__ = _BOOTSTRAP_SCRIPTS
    sys.modules[_BOOTSTRAP_ROOT] = root_package
    sys.modules[_BOOTSTRAP_SCRIPTS] = scripts_package
    contracts = importlib.import_module(
        _BOOTSTRAP_SCRIPTS + ".delegation_contracts"
    )


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
            if (
                contracts.canonical_json(event).encode("utf-8") + b"\n"
                != raw_line
            ):
                raise LedgerError(
                    "event line is not exact canonical JSON followed by LF"
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
    if (
        value["valid_prefix_byte_count"] + value["discarded_tail_byte_count"]
        > MAX_LEDGER_BYTES
    ):
        raise LedgerError("repair intent before state exceeds ledger capacity")
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
    if (value["valid_prefix_record_count"] == 0) != (
        value["last_valid_record_digest"] is None
    ):
        raise LedgerError(
            "repair intent prefix count and last digest are inconsistent"
        )
    if sequence is not None and sequence != value["valid_prefix_record_count"] + 1:
        raise LedgerError(
            "repair intent extractable_sequence is not the exact next sequence"
        )
    quarantine_ref = value["quarantine_ref"]
    quarantine_digest = value["quarantine_digest"]
    if (quarantine_ref is None) != (quarantine_digest is None):
        raise LedgerError("repair quarantine metadata is incomplete")
    if quarantine_ref is not None:
        contracts.validate_reference(quarantine_ref, "quarantine_ref")
        contracts.validate_digest(quarantine_digest, "quarantine_digest")
        expected_ref = "repair-quarantine/{}.bin".format(
            str(value["before_digest"]).split(":", 1)[1]
        )
        if quarantine_ref != expected_ref:
            raise LedgerError(
                "repair quarantine reference is not derived from before_digest"
            )
        if quarantine_digest != value["discarded_tail_digest"]:
            raise LedgerError(
                "repair quarantine digest does not equal discarded tail digest"
            )
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
        intent = _validate_repair_intent(value, run_id)
        expected_name = "{}.json".format(
            str(intent["before_digest"]).split(":", 1)[1]
        )
        if path.name != expected_name:
            raise LedgerError(
                "repair intent filename is not derived from before_digest"
            )
        if contracts.canonical_json(intent).encode("utf-8") + b"\n" != raw:
            raise LedgerError(
                "repair intent is not exact canonical JSON followed by LF"
            )
        return intent
    except (UnicodeDecodeError, contracts.ContractError, LedgerError) as exc:
        raise LedgerError(
            "malformed repair intent {}: {}".format(path.name, exc)
        ) from exc


class _IncompleteJson(Exception):
    def __init__(self, classification: str) -> None:
        super().__init__(classification)
        self.classification = classification


_JSON_NUMBER = re.compile(
    r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
)
_INCOMPLETE_JSON_NUMBER = re.compile(
    r"(?:-|-?(?:0|[1-9][0-9]*)\.|"
    r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?[eE][+-]?)"
)


class _StructuralPrefixScanner:
    """Recognize only a bounded prefix of one strict JSON object.

    This scanner never asks CPython's recursive JSON decoder to classify an
    incomplete document. Completed scalar tokens still pass through the v2
    strict loader so integer, float, constant, and string behavior stays
    aligned with persisted contracts.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.index = 0
        self.sequence: Optional[int] = None

    def scan(self) -> tuple[str, Optional[int]]:
        if not self.text or self.text[0] != "{":
            raise LedgerError(
                "repair refused because torn tail is not a JSON object prefix"
            )
        try:
            self._parse_value(0)
        except _IncompleteJson as exc:
            return exc.classification, self.sequence
        except contracts.ContractError as exc:
            raise LedgerError(
                "repair refused because torn tail violates strict JSON: {}".format(
                    exc
                )
            ) from exc
        except (RecursionError, ValueError, OverflowError) as exc:
            raise LedgerError(
                "repair refused because torn tail exceeds strict JSON bounds"
            ) from exc
        if self.index != len(self.text):
            raise LedgerError(
                "repair refused because tail contains trailing corruption"
            )
        raise LedgerError(
            "repair refused because a complete record missing only newline is ambiguous"
        )

    def _parse_value(self, depth: int, *, require_integer: bool = False) -> object:
        if depth > contracts.MAX_JSON_DEPTH:
            raise LedgerError(
                "repair refused because torn tail exceeds the JSON depth bound"
            )
        if self.index >= len(self.text):
            raise _IncompleteJson("truncated_json")
        char = self.text[self.index]
        if require_integer and not char.isdigit():
            raise LedgerError(
                "repair refused because extractable sequence is not an integer"
            )
        if char == "{":
            if require_integer:
                raise LedgerError(
                    "repair refused because extractable sequence is not an integer"
                )
            return self._parse_object(depth)
        if char == "[":
            if require_integer:
                raise LedgerError(
                    "repair refused because extractable sequence is not an integer"
                )
            return self._parse_array(depth)
        if char == '"':
            if require_integer:
                raise LedgerError(
                    "repair refused because extractable sequence is not an integer"
                )
            return self._parse_string()
        if char in "-0123456789":
            return self._parse_number(require_integer=require_integer)
        if require_integer:
            raise LedgerError(
                "repair refused because extractable sequence is not an integer"
            )
        if char == "t":
            return self._parse_literal("true", True)
        if char == "f":
            return self._parse_literal("false", False)
        if char == "n":
            return self._parse_literal("null", None)
        if char in "NI":
            raise LedgerError(
                "repair refused because tail contains a non-finite JSON constant"
            )
        raise LedgerError(
            "repair refused because tail corruption is not terminal/structural"
        )

    def _parse_object(self, depth: int) -> Dict[str, object]:
        self.index += 1
        result: Dict[str, object] = {}
        if self.index >= len(self.text):
            raise _IncompleteJson("truncated_json")
        if self.text[self.index] == "}":
            self.index += 1
            return result
        while True:
            if self.index >= len(self.text):
                raise _IncompleteJson("truncated_json")
            if self.text[self.index] != '"':
                raise LedgerError(
                    "repair refused because object key syntax is invalid"
                )
            key = self._parse_string()
            if not isinstance(key, str):
                raise LedgerError("repair refused because object key is not text")
            if key in result:
                raise LedgerError(
                    "repair refused because torn tail has duplicate completed "
                    "object key {!r}".format(key)
                )
            # Record a completed key before parsing its value so a duplicate is
            # rejected even when the containing object remains incomplete.
            result[key] = None
            if self.index >= len(self.text):
                raise _IncompleteJson("truncated_json")
            if self.text[self.index] != ":":
                raise LedgerError(
                    "repair refused because object key is not followed by colon"
                )
            self.index += 1
            is_root_sequence = depth == 0 and key == "sequence"
            value = self._parse_value(
                depth + 1,
                require_integer=is_root_sequence,
            )
            result[key] = value
            if is_root_sequence:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                    or value > MAX_RECORDS
                ):
                    raise LedgerError(
                        "repair refused because extractable sequence is invalid"
                    )
                self.sequence = value
            if self.index >= len(self.text):
                raise _IncompleteJson("truncated_json")
            delimiter = self.text[self.index]
            if delimiter == "}":
                self.index += 1
                return result
            if delimiter != ",":
                raise LedgerError(
                    "repair refused because object delimiter is invalid"
                )
            self.index += 1

    def _parse_array(self, depth: int) -> List[object]:
        self.index += 1
        result: List[object] = []
        if self.index >= len(self.text):
            raise _IncompleteJson("truncated_json")
        if self.text[self.index] == "]":
            self.index += 1
            return result
        while True:
            result.append(self._parse_value(depth + 1))
            if self.index >= len(self.text):
                raise _IncompleteJson("truncated_json")
            delimiter = self.text[self.index]
            if delimiter == "]":
                self.index += 1
                return result
            if delimiter != ",":
                raise LedgerError(
                    "repair refused because array delimiter is invalid"
                )
            self.index += 1

    def _parse_string(self) -> str:
        start = self.index
        self.index += 1
        while self.index < len(self.text):
            char = self.text[self.index]
            if char == '"':
                self.index += 1
                token = self.text[start : self.index]
                value = contracts.strict_json_loads(token)
                if not isinstance(value, str):
                    raise LedgerError("repair refused because string token is invalid")
                return value
            if ord(char) < 0x20:
                raise LedgerError(
                    "repair refused because string contains a control character"
                )
            if char != "\\":
                self.index += 1
                continue
            self.index += 1
            if self.index >= len(self.text):
                raise _IncompleteJson("unterminated_string")
            escape = self.text[self.index]
            if escape not in '"\\/bfnrtu':
                raise LedgerError(
                    "repair refused because string escape is invalid"
                )
            if escape != "u":
                self.index += 1
                continue
            available = len(self.text) - (self.index + 1)
            count = min(4, available)
            digits = self.text[self.index + 1 : self.index + 1 + count]
            if any(char not in "0123456789abcdefABCDEF" for char in digits):
                raise LedgerError(
                    "repair refused because Unicode escape is invalid"
                )
            if available < 4:
                raise _IncompleteJson("unterminated_string")
            self.index += 5
        raise _IncompleteJson("unterminated_string")

    def _parse_literal(self, token: str, value: object) -> object:
        remaining = self.text[self.index :]
        if len(remaining) < len(token):
            if token.startswith(remaining):
                raise _IncompleteJson("truncated_json")
            raise LedgerError(
                "repair refused because JSON literal is invalid"
            )
        if not remaining.startswith(token):
            raise LedgerError("repair refused because JSON literal is invalid")
        self.index += len(token)
        return value

    def _parse_number(self, *, require_integer: bool) -> object:
        start = self.index
        while (
            self.index < len(self.text)
            and self.text[self.index] not in ",]}"
        ):
            self.index += 1
        token = self.text[start : self.index]
        at_end = self.index == len(self.text)
        if require_integer and any(char not in "0123456789" for char in token):
            raise LedgerError(
                "repair refused because extractable sequence is not an integer"
            )
        if _JSON_NUMBER.fullmatch(token):
            value = contracts.strict_json_loads(token)
            if require_integer and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise LedgerError(
                    "repair refused because extractable sequence is not an integer"
                )
            return value
        if at_end and _INCOMPLETE_JSON_NUMBER.fullmatch(token):
            raise _IncompleteJson("truncated_json")
        raise LedgerError(
            "repair refused because JSON number is invalid"
        )


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

    try:
        text = tail.decode("utf-8")
    except UnicodeDecodeError as exc:
        if exc.end != len(tail) or exc.reason != "unexpected end of data":
            raise LedgerError(
                "repair refused because tail UTF-8 corruption is not terminal"
            ) from exc
        decoded_prefix = tail[: exc.start].decode("utf-8")
        classification, sequence = _StructuralPrefixScanner(
            decoded_prefix
        ).scan()
        if classification != "unterminated_string":
            raise LedgerError(
                "repair refused because terminal UTF-8 truncation is not "
                "inside a structurally valid string"
            )
        expected_sequence = len(prefix_records) + 1
        if expected_sequence > MAX_RECORDS:
            raise LedgerError(
                "repair refused because the next sequence exceeds capacity"
            )
        if sequence is not None and sequence != expected_sequence:
            raise LedgerError(
                "repair refused because extractable sequence is not the next record"
            )
        return (
            prefix,
            tail,
            "truncated_utf8_codepoint",
            sequence,
            prefix_records,
        )

    classification, sequence = _StructuralPrefixScanner(text).scan()
    expected_sequence = len(prefix_records) + 1
    if expected_sequence > MAX_RECORDS:
        raise LedgerError(
            "repair refused because the next sequence exceeds capacity"
        )
    if sequence is not None and sequence != expected_sequence:
        raise LedgerError(
            "repair refused because extractable sequence is not the next record"
        )
    return prefix, tail, classification, sequence, prefix_records


def _read_repair_artifact(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise LedgerError("could not read {}: {}".format(label, exc)) from exc


def _validate_candidate_bytes(
    intent: Mapping[str, object],
    candidate: bytes,
    run_id: str,
) -> List[Mapping[str, object]]:
    if len(candidate) != intent["valid_prefix_byte_count"]:
        raise LedgerError(
            "repair candidate length does not match intent prefix length"
        )
    if contracts.digest_bytes(candidate) != intent["candidate_repaired_digest"]:
        raise LedgerError("repair candidate digest does not match intent")
    records, report = _read_records_bytes(candidate, run_id)
    if not report["valid"]:
        raise LedgerError(
            "repair candidate is not a canonical valid ledger: {}".format(
                report["corruption"]
            )
        )
    if len(records) != intent["valid_prefix_record_count"]:
        raise LedgerError(
            "repair candidate record count does not match intent"
        )
    last_digest = records[-1]["record_digest"] if records else None
    if last_digest != intent["last_valid_record_digest"]:
        raise LedgerError(
            "repair candidate last digest does not match intent"
        )
    next_sequence = len(records) + 1
    if next_sequence > MAX_RECORDS:
        raise LedgerError(
            "repair candidate has no reachable next sequence within capacity"
        )
    if (
        intent["extractable_sequence"] is not None
        and intent["extractable_sequence"] != next_sequence
    ):
        raise LedgerError(
            "repair intent extractable sequence is not candidate next sequence"
        )
    return records


def _validate_quarantine_relation(
    intent: Mapping[str, object],
    directory: Path,
    *,
    tail: Optional[bytes],
    required: bool,
) -> Optional[bytes]:
    before_hex = str(intent["before_digest"]).split(":", 1)[1]
    expected_ref = "repair-quarantine/{}.bin".format(before_hex)
    expected_path = directory / expected_ref
    selected_ref = intent["quarantine_ref"]
    if selected_ref is None:
        if expected_path.exists():
            raise LedgerError(
                "unselected repair quarantine conflicts with intent"
            )
        return None
    if selected_ref != expected_ref:
        raise LedgerError(
            "repair quarantine path does not match before_digest"
        )
    if intent["quarantine_digest"] != intent["discarded_tail_digest"]:
        raise LedgerError(
            "repair quarantine digest does not match discarded tail"
        )
    if not expected_path.exists():
        if required:
            raise LedgerError(
                "repair quarantine is required before completed replay"
            )
        return None
    quarantine = _read_repair_artifact(
        expected_path, "repair quarantine"
    )
    if len(quarantine) != intent["discarded_tail_byte_count"]:
        raise LedgerError(
            "repair quarantine length does not match discarded tail"
        )
    if contracts.digest_bytes(quarantine) != intent["discarded_tail_digest"]:
        raise LedgerError(
            "repair quarantine digest does not match discarded tail"
        )
    if tail is not None and quarantine != tail:
        raise LedgerError(
            "repair quarantine bytes do not match reachable discarded tail"
        )
    return quarantine


def _validate_intent_relation(
    intent: Mapping[str, object],
    current: bytes,
    run_id: str,
    directory: Path,
) -> Dict[str, object]:
    """Prove one immutable intent is reachable from the exact current bytes."""
    before_hex = str(intent["before_digest"]).split(":", 1)[1]
    candidate_path = directory / (
        "events.repair-{}.candidate".format(before_hex)
    )
    current_digest = contracts.digest_bytes(current)

    if current_digest == intent["before_digest"]:
        prefix, tail, classification, sequence, prefix_records = (
            _classify_torn_tail(current, run_id)
        )
        expected = {
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
        }
        for field, expected_value in expected.items():
            if intent[field] != expected_value:
                raise LedgerError(
                    "repair intent {} does not match reachable before "
                    "state".format(field)
                )
        if candidate_path.exists():
            candidate = _read_repair_artifact(
                candidate_path, "repair candidate"
            )
            if candidate != prefix:
                raise LedgerError(
                    "repair candidate is not the exact reachable prefix"
                )
            _validate_candidate_bytes(intent, candidate, run_id)
        _validate_quarantine_relation(
            intent,
            directory,
            tail=tail,
            required=candidate_path.exists(),
        )
        return {
            "state": "before",
            "prefix": prefix,
            "tail": tail,
            "prefix_records": prefix_records,
        }

    prefix_length = intent["valid_prefix_byte_count"]
    if not isinstance(prefix_length, int) or len(current) < prefix_length:
        raise LedgerError(
            "repair intent candidate prefix is unreachable from current ledger"
        )
    candidate = current[:prefix_length]
    _validate_candidate_bytes(intent, candidate, run_id)
    if candidate_path.exists():
        prepared = _read_repair_artifact(
            candidate_path, "repair candidate"
        )
        if prepared != candidate:
            raise LedgerError(
                "prepared repair candidate conflicts with current prefix"
            )
        _validate_candidate_bytes(intent, prepared, run_id)

    if (
        len(current) == prefix_length
        and current_digest == intent["candidate_repaired_digest"]
    ):
        state = "completed"
    else:
        records, report = _read_records_bytes(current, run_id)
        if not report["valid"]:
            raise LedgerError(
                "later ledger bytes after repair are not a canonical valid "
                "stream: {}".format(report["corruption"])
            )
        if len(records) < intent["valid_prefix_record_count"]:
            raise LedgerError(
                "later ledger stream has fewer records than repair candidate"
            )
        state = "appended"

    quarantine = _validate_quarantine_relation(
        intent,
        directory,
        tail=None,
        required=True,
    )
    if quarantine is not None and contracts.digest_bytes(
        candidate + quarantine
    ) != intent["before_digest"]:
        raise LedgerError(
            "repair candidate and quarantine do not reconstruct before_digest"
        )
    return {
        "state": state,
        "prefix": candidate,
        "tail": quarantine,
        "prefix_records": (),
    }


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

            intents: List[
                tuple[Dict[str, object], Dict[str, object]]
            ] = []
            if self.intent_directory.exists():
                try:
                    intent_entries = sorted(self.intent_directory.iterdir())
                except OSError as exc:
                    raise LedgerError(
                        "could not enumerate repair intents: {}".format(exc)
                    ) from exc
                if any(
                    not entry.is_file() or entry.suffix != ".json"
                    for entry in intent_entries
                ):
                    raise LedgerError(
                        "unexpected repair-intent artifact blocks manual recovery"
                    )
                for intent_path in intent_entries:
                    intent = _read_intent(intent_path, self.run_id)
                    relation = _validate_intent_relation(
                        intent,
                        data,
                        self.run_id,
                        self.directory,
                    )
                    intents.append((intent, relation))

            matching_pair = next(
                (
                    (intent, relation)
                    for intent, relation in intents
                    if intent["before_digest"] == expected_digest
                ),
                None,
            )
            matching = matching_pair[0] if matching_pair is not None else None
            matching_relation = (
                matching_pair[1] if matching_pair is not None else None
            )
            if current_digest != expected_digest:
                if (
                    matching is not None
                    and matching_relation is not None
                    and matching_relation["state"] in {"completed", "appended"}
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

            if matching_relation is not None:
                if matching_relation["state"] != "before":
                    raise LedgerError(
                        "matching repair intent is not in a reachable before state"
                    )
                prefix = matching_relation["prefix"]
                tail = matching_relation["tail"]
                prefix_records = matching_relation["prefix_records"]
                if not isinstance(prefix, bytes) or not isinstance(tail, bytes):
                    raise LedgerError(
                        "matching repair intent has impossible reachable bytes"
                    )
                if not isinstance(prefix_records, list):
                    raise LedgerError(
                        "matching repair intent has impossible prefix records"
                    )
                classification = str(matching["structural_classification"])
                sequence = matching["extractable_sequence"]
            else:
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
            candidate_path = self.directory / (
                "events.repair-{}.candidate".format(before_hex)
            )
            derived_quarantine_path = self.quarantine_directory / (
                "{}.bin".format(before_hex)
            )
            if matching is None:
                if candidate_path.exists() or derived_quarantine_path.exists():
                    raise LedgerError(
                        "orphaned repair artifact blocks manual recovery"
                    )
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
                _validate_candidate_bytes(proposed, candidate_bytes, self.run_id)
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
            _validate_candidate_bytes(proposed, prefix, self.run_id)
            _validate_quarantine_relation(
                proposed,
                self.directory,
                tail=tail,
                required=True,
            )
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
