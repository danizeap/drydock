from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

import pytest

from adapters.codex.drydock.scripts import delegation_contracts as contracts
from adapters.codex.drydock.scripts import delegation_ledger


NOW = "2026-07-28T12:00:00.000Z"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def append_event(
    ledger: delegation_ledger.RunLedger,
    number: int = 1,
) -> Mapping[str, object]:
    return ledger.append(
        event_type="delegation_event",
        runtime_status="completed",
        payload={"number": number},
        event_id="event-{}".format(number),
        recorded_at=NOW,
    )


def add_torn_tail(ledger: delegation_ledger.RunLedger) -> str:
    append_event(ledger)
    with ledger.path.open("ab") as stream:
        stream.write(
            b'{"schema_version":2,"sequence":2,"event_id":"torn-event'
        )
        stream.flush()
        os.fsync(stream.fileno())
    return contracts.digest_bytes(ledger.path.read_bytes())


def test_append_persists_v2_canonical_sequence_and_honest_limitations(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    first = append_event(target, 1)
    second = append_event(target, 2)

    assert first["schema_version"] == 2
    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert second["previous_record_digest"] == first["record_digest"]
    lines = target.path.read_text(encoding="utf-8").splitlines()
    assert lines == [
        contracts.canonical_json(contracts.strict_json_loads(line))
        for line in lines
    ]
    report = target.verify()
    assert report["valid"] is True
    assert report["record_count"] == 2
    assert report["authenticity"] == "not_established"
    assert report["suffix_completeness"] == "not_established"
    assert "user-writable" in " ".join(report["limitations"])
    assert "not ruled out" in " ".join(report["limitations"])


def test_read_only_empty_ledger_calls_do_not_mutate_filesystem(
    tmp_path: Path,
) -> None:
    root = tmp_path / "absent"
    target = delegation_ledger.RunLedger(root, "run-1")
    before = list(tmp_path.rglob("*"))

    assert target.verify()["valid"] is True
    assert target.read_records() == []
    assert list(tmp_path.rglob("*")) == before
    assert not target.lock_path.exists()
    assert not target.directory.exists()


def test_payload_is_detached_before_persistence(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    payload = {"claims": [{"state": "initial"}]}
    target.append(
        event_type="claim_observed",
        runtime_status="completed",
        payload=payload,
        event_id="event-1",
        recorded_at=NOW,
    )
    before = target.path.read_bytes()
    payload["claims"][0]["state"] = "mutated"  # type: ignore[index]
    payload["claims"].append({"state": "outside"})  # type: ignore[union-attr]

    assert target.path.read_bytes() == before
    assert target.read_records()[0]["payload"] == {
        "claims": [{"state": "initial"}]
    }


def test_tamper_and_v1_are_reported_and_prevent_append(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    append_event(target)
    record = contracts.strict_json_loads(
        target.path.read_text(encoding="utf-8").strip()
    )
    assert isinstance(record, dict)
    record["schema_version"] = 1
    target.path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    report = target.verify()
    assert report["valid"] is False
    assert report["corruption"]["line"] == 1
    assert "v2 required" in report["corruption"]["reason"]
    before = target.path.read_bytes()
    with pytest.raises(delegation_ledger.LedgerError, match="corrupt"):
        append_event(target, 2)
    assert target.path.read_bytes() == before


def test_reordering_and_incomplete_final_line_fail_closed(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    append_event(target, 1)
    append_event(target, 2)
    lines = target.path.read_bytes().splitlines(keepends=True)
    target.path.write_bytes(lines[1] + lines[0])
    assert target.verify()["valid"] is False

    target.path.write_bytes(lines[0].rstrip(b"\n"))
    report = target.verify()
    assert report["valid"] is False
    assert "newline-terminated" in report["corruption"]["reason"]


def _noncanonical_line(raw: bytes, mutation: str) -> bytes:
    if mutation == "leading_whitespace":
        return b" " + raw
    if mutation == "trailing_whitespace":
        return raw[:-1] + b" \n"
    if mutation == "interior_whitespace":
        return raw.replace(b":", b": ", 1)
    if mutation == "crlf":
        return raw[:-1] + b"\r\n"
    if mutation == "key_order":
        value = contracts.strict_json_loads(raw[:-1].decode("utf-8"))
        assert isinstance(value, dict)
        reordered = {
            key: value[key] for key in reversed(tuple(value))
        }
        return (
            json.dumps(
                reordered,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    if mutation == "escaping":
        assert b"safe/path" in raw
        return raw.replace(b"safe/path", b"safe\\/path", 1)
    raise AssertionError("unknown mutation")


@pytest.mark.parametrize(
    "mutation",
    [
        "leading_whitespace",
        "trailing_whitespace",
        "interior_whitespace",
        "crlf",
        "key_order",
        "escaping",
    ],
)
def test_noncanonical_event_bytes_block_replay_and_append(
    tmp_path: Path,
    mutation: str,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path / mutation, "run-1")
    target.append(
        event_type="delegation_event",
        runtime_status="completed",
        payload={"label": "safe/path"},
        event_id="event-1",
        recorded_at=NOW,
    )
    mutated = _noncanonical_line(target.path.read_bytes(), mutation)
    target.path.write_bytes(mutated)

    report = target.verify()
    assert report["valid"] is False
    assert "canonical JSON" in report["corruption"]["reason"]
    before = target.path.read_bytes()
    with pytest.raises(delegation_ledger.LedgerError, match="corrupt"):
        append_event(target, 2)
    assert target.path.read_bytes() == before


def test_sensitive_or_oversized_payload_is_rejected_before_ledger_creation(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    with pytest.raises(contracts.ContractError, match="forbidden"):
        target.append(
            event_type="delegation_started",
            runtime_status="started",
            payload={"raw_response": "provider body"},
        )
    with pytest.raises(contracts.ContractError, match="byte bound"):
        target.append(
            event_type="delegation_started",
            runtime_status="started",
            payload={"summary": "x" * 513},
        )
    assert not target.path.exists()


def test_repair_event_type_is_reserved_from_ordinary_append(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")

    with pytest.raises(delegation_ledger.LedgerError, match="reserved"):
        target.append(
            event_type=delegation_ledger.REPAIR_EVENT_TYPE,
            runtime_status="repaired",
            payload={},
            event_id="forged-repair",
            recorded_at=NOW,
        )

    assert not target.directory.exists()


def test_canonical_round_trip_corpus_preserves_exact_code_points() -> None:
    corpus = [
        {"text": 'braces {}[] and quote " plus slash \\'},
        {"escaped": 'prefix "quoted" suffix', "nested": [[1, 2], [3, 4]]},
        {"unicode_escape_text": "\u20ac", "supplementary": "\U0001f680"},
        {"composed": "\u00e9", "decomposed": "e\u0301"},
    ]

    for value in corpus:
        first = contracts.canonical_json(value)
        parsed = contracts.strict_json_loads(first)
        second = contracts.canonical_json(parsed)
        assert second == first

    composed = contracts.canonical_json({"value": "\u00e9"})
    decomposed = contracts.canonical_json({"value": "e\u0301"})
    assert composed != decomposed
    assert contracts.digest_text(composed) != contracts.digest_text(decomposed)


@pytest.mark.skipif(os.name not in {"nt", "posix"}, reason="unsupported lock OS")
def test_eight_processes_append_three_events_without_torn_lines(
    tmp_path: Path,
) -> None:
    writer_count = 8
    events_per_writer = 3
    ready_directory = tmp_path / "writer-ready"
    ready_directory.mkdir()
    start_gate = tmp_path / "writer-start"
    script = """
import sys
import time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from adapters.codex.drydock.scripts.delegation_ledger import RunLedger
target = RunLedger(Path(sys.argv[2]), "shared-run")
worker = sys.argv[3]
(Path(sys.argv[5]) / worker).write_bytes(b"ready")
deadline = time.monotonic() + 20
while not Path(sys.argv[6]).exists():
    if time.monotonic() >= deadline:
        raise RuntimeError("writer start gate timed out")
    time.sleep(0.01)
for number in range(int(sys.argv[4])):
    target.append(
        event_type="worker_event",
        runtime_status="completed",
        payload={"worker": worker, "number": number},
        event_id="event-" + worker + "-" + str(number),
        recorded_at="2026-07-28T12:00:00.000Z",
    )
"""
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(REPOSITORY_ROOT),
                str(tmp_path),
                str(worker),
                str(events_per_writer),
                str(ready_directory),
                str(start_gate),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for worker in range(writer_count)
    ]
    failures = []
    try:
        ready_deadline = time.monotonic() + 20
        while len(list(ready_directory.iterdir())) != writer_count:
            early_exits = [
                process.returncode
                for process in processes
                if process.poll() is not None
            ]
            assert early_exits == [], "writer exited before contention gate"
            assert time.monotonic() < ready_deadline, "writers did not become ready"
            time.sleep(0.01)
        start_gate.write_bytes(b"go")

        deadline = time.monotonic() + 45
        for process in processes:
            remaining = deadline - time.monotonic()
            assert remaining > 0, (
                "subprocess contention harness exceeded its bound"
            )
            stdout, stderr = process.communicate(timeout=remaining)
            if process.returncode != 0:
                failures.append((process.returncode, stdout, stderr))
    finally:
        unfinished = [process for process in processes if process.poll() is None]
        for process in unfinished:
            process.terminate()
        for process in unfinished:
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
    assert failures == []
    assert [process.returncode for process in processes] == [0] * writer_count

    target = delegation_ledger.RunLedger(tmp_path, "shared-run")
    records = target.read_records()
    expected_count = writer_count * events_per_writer
    sequences = [record["sequence"] for record in records]
    event_ids = [record["event_id"] for record in records]
    assert sequences == list(range(1, expected_count + 1))
    assert len(sequences) == len(set(sequences)) == expected_count
    assert len(event_ids) == len(set(event_ids)) == expected_count
    assert set(event_ids) == {
        "event-{}-{}".format(worker, number)
        for worker in range(writer_count)
        for number in range(events_per_writer)
    }
    raw = target.path.read_bytes()
    lines = raw.splitlines(keepends=True)
    assert len(lines) == expected_count
    assert raw.endswith(b"\n")
    assert all(
        line.endswith(b"\n") and not line.endswith(b"\r\n")
        for line in lines
    )
    assert all(
        contracts.canonical_json(
            contracts.strict_json_loads(line[:-1].decode("utf-8"))
        ).encode("utf-8")
        + b"\n"
        == line
        for line in lines
    )
    report = target.verify()
    assert report["valid"] is True
    assert report["record_count"] == expected_count
    assert target.lock_path.read_bytes() == b"\0"


def test_direct_cli_help_works_from_source_and_installed_scripts_layout(
    tmp_path: Path,
) -> None:
    source_scripts = Path(delegation_ledger.__file__).resolve().parent
    installed_scripts = tmp_path / "plugin-root" / "scripts"
    installed_scripts.mkdir(parents=True)
    for name in ("delegation_contracts.py", "delegation_ledger.py"):
        (installed_scripts / name).write_bytes(
            (source_scripts / name).read_bytes()
        )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    for script in (
        source_scripts / "delegation_ledger.py",
        installed_scripts / "delegation_ledger.py",
    ):
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert "repair-torn-tail" in completed.stdout
        assert "ImportError" not in completed.stderr


@pytest.mark.skipif(os.name not in {"nt", "posix"}, reason="unsupported lock OS")
def test_real_lock_contention_times_out_deterministically(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "contention" / ".events.lock"
    marker = tmp_path / "lock-held"
    script = """
import sys
import time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from adapters.codex.drydock.scripts.delegation_ledger import exclusive_file_lock
with exclusive_file_lock(Path(sys.argv[2]), timeout_s=1.0):
    Path(sys.argv[3]).write_text("held", encoding="utf-8")
    time.sleep(5)
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            script,
            str(REPOSITORY_ROOT),
            str(lock_path),
            str(marker),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and process.poll() is None:
            if time.monotonic() >= deadline:
                pytest.fail("lock holder did not become ready")
            time.sleep(0.01)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                "lock holder exited early: {!r} {!r}".format(stdout, stderr)
            )
        with pytest.raises(delegation_ledger.LedgerError, match="timed out"):
            with delegation_ledger.exclusive_file_lock(
                lock_path, timeout_s=0.1
            ):
                pytest.fail("contended lock was acquired")
    finally:
        process.terminate()
        process.communicate(timeout=10)
    reacquired = False
    with delegation_ledger.exclusive_file_lock(lock_path, timeout_s=1.0):
        reacquired = True
    assert reacquired is True
    assert lock_path.read_bytes() == b"\0"


@pytest.mark.parametrize(
    ("fault_step", "quarantine"),
    [
        ("pre_intent", False),
        ("post_intent", False),
        ("post_quarantine", True),
        ("post_candidate", False),
        ("post_replace", False),
    ],
)
def test_repair_replays_idempotently_after_every_durable_step(
    tmp_path: Path,
    fault_step: str,
    quarantine: bool,
) -> None:
    target = delegation_ledger.RunLedger(
        tmp_path / fault_step, "run-repair"
    )
    expected_digest = add_torn_tail(target)
    valid_prefix = target.path.read_bytes().split(b"\n", 1)[0] + b"\n"

    with pytest.raises(delegation_ledger.RepairInterrupted):
        target.repair_torn_tail(
            expected_digest=expected_digest,
            quarantine=quarantine,
            _fault_after=fault_step,
        )
    if fault_step == "post_replace":
        immediate = target.verify()
        assert immediate["valid"] is True
        assert immediate["repair_history_count"] == 1
        assert target.read_records()[-1]["event_type"] == (
            delegation_ledger.REPAIR_EVENT_TYPE
        )
    repaired = target.repair_torn_tail(
        expected_digest=expected_digest,
        quarantine=quarantine,
    )
    assert repaired["status"] in {"repaired", "completed_replay"}
    repaired_bytes = target.path.read_bytes()
    assert repaired_bytes.startswith(valid_prefix)
    assert repaired_bytes != valid_prefix
    records = target.read_records()
    assert records[-1]["event_type"] == delegation_ledger.REPAIR_EVENT_TYPE
    marker = records[-1]
    report = target.verify()
    assert report["valid"] is True
    assert report["repair_history_count"] == 1
    assert report["has_repair_history"] is True

    replay = target.repair_torn_tail(
        expected_digest=expected_digest,
        quarantine=quarantine,
    )
    assert replay["status"] == "completed_replay"
    assert target.path.read_bytes() == repaired_bytes
    intents = list(target.intent_directory.glob("*.json"))
    assert len(intents) == 1
    intent = contracts.strict_json_loads(
        intents[0].read_text(encoding="utf-8")
    )
    assert isinstance(intent, dict)
    assert marker["payload"] == {
        "intent_id": intent["intent_id"],
        "before_digest": intent["before_digest"],
        "discarded_tail_digest": intent["discarded_tail_digest"],
        "discarded_tail_byte_count": intent["discarded_tail_byte_count"],
        "structural_classification": intent["structural_classification"],
        "valid_prefix_record_count": intent["valid_prefix_record_count"],
        "valid_prefix_byte_count": intent["valid_prefix_byte_count"],
        "extractable_sequence": intent["extractable_sequence"],
        "quarantine_ref": intent["quarantine_ref"],
    }
    assert intent["candidate_repaired_digest"] == contracts.digest_bytes(
        repaired_bytes
    )
    assert intent["candidate_byte_count"] == len(repaired_bytes)
    assert intent["candidate_record_count"] == len(records)
    assert intent["candidate_last_record_digest"] == marker["record_digest"]
    if quarantine:
        quarantines = list(target.quarantine_directory.glob("*.bin"))
        assert len(quarantines) == 1


def test_repair_refuses_stale_digest_without_changing_bytes(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected_digest = add_torn_tail(target)
    before = target.path.read_bytes()
    stale = "sha256:" + ("0" * 64)

    with pytest.raises(delegation_ledger.LedgerError, match="stale"):
        target.repair_torn_tail(expected_digest=stale)
    assert target.path.read_bytes() == before
    assert expected_digest == contracts.digest_bytes(before)


def test_repair_refuses_newline_semantic_interior_and_ambiguous_tail(
    tmp_path: Path,
) -> None:
    newline_target = delegation_ledger.RunLedger(tmp_path / "newline", "run-1")
    append_event(newline_target)
    with newline_target.path.open("ab") as stream:
        stream.write(b"{}\n")
    newline_digest = contracts.digest_bytes(newline_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="non-newline"):
        newline_target.repair_torn_tail(expected_digest=newline_digest)

    interior_target = delegation_ledger.RunLedger(tmp_path / "interior", "run-1")
    append_event(interior_target)
    data = bytearray(interior_target.path.read_bytes())
    data[data.index(b"completed")] = ord("x")
    data.extend(b'{"sequence":2,"event_id":"torn')
    interior_target.path.write_bytes(bytes(data))
    interior_digest = contracts.digest_bytes(interior_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="prefix is corrupt"):
        interior_target.repair_torn_tail(expected_digest=interior_digest)

    ambiguous_target = delegation_ledger.RunLedger(
        tmp_path / "ambiguous", "run-1"
    )
    append_event(ambiguous_target)
    complete = append_event(ambiguous_target, 2)
    assert complete["sequence"] == 2
    ambiguous_target.path.write_bytes(
        ambiguous_target.path.read_bytes().rstrip(b"\n")
    )
    ambiguous_digest = contracts.digest_bytes(
        ambiguous_target.path.read_bytes()
    )
    with pytest.raises(delegation_ledger.LedgerError, match="ambiguous"):
        ambiguous_target.repair_torn_tail(expected_digest=ambiguous_digest)

    semantic_target = delegation_ledger.RunLedger(
        tmp_path / "semantic", "run-1"
    )
    append_event(semantic_target)
    with semantic_target.path.open("ab") as stream:
        stream.write(b'{"sequence":2,"value":NaN')
    semantic_digest = contracts.digest_bytes(semantic_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="non-finite"):
        semantic_target.repair_torn_tail(expected_digest=semantic_digest)

    sequence_target = delegation_ledger.RunLedger(
        tmp_path / "sequence", "run-1"
    )
    append_event(sequence_target)
    with sequence_target.path.open("ab") as stream:
        stream.write(b'{"sequence":9,"event_id":"torn')
    sequence_digest = contracts.digest_bytes(sequence_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="not the next"):
        sequence_target.repair_torn_tail(expected_digest=sequence_digest)


@pytest.mark.parametrize(
    "tail",
    [
        b'{"sequence":2,"payload":1e400',
        b'{"sequence":' + (b"9" * 5000),
        b'{"sequence":2,"sequence":',
        b'{"sequence":2,"payload":'
        + (b"[" * (contracts.MAX_JSON_DEPTH + 1)),
    ],
)
def test_torn_tail_classifier_returns_typed_error_for_adversarial_prefixes(
    tmp_path: Path,
    tail: bytes,
) -> None:
    target = delegation_ledger.RunLedger(
        tmp_path / contracts.digest_bytes(tail)[-12:], "run-1"
    )
    append_event(target)
    with target.path.open("ab") as stream:
        stream.write(tail)
    expected = contracts.digest_bytes(target.path.read_bytes())
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError):
        target.repair_torn_tail(expected_digest=expected)
    assert target.path.read_bytes() == before


@pytest.mark.parametrize(
    "tail",
    [
        b'{"sequence":2,"payload":{"note":"braces }{[] and quote \\" open',
        b'{"sequence":2,"payload":{"note":"truncated escape \\',
        b'{"sequence":2,"payload":{"note":"unicode \\u12',
        b'{"sequence":2,"payload":{"note":"surrogate \\ud83d\\u',
        b'{"sequence":2,"payload":[[[["nested braces { in string',
    ],
)
def test_bounded_string_escape_and_nested_array_truncations_are_repairable(
    tmp_path: Path,
    tail: bytes,
) -> None:
    target = delegation_ledger.RunLedger(
        tmp_path / contracts.digest_bytes(tail)[-12:], "run-1"
    )
    append_event(target)
    with target.path.open("ab") as stream:
        stream.write(tail)
        stream.flush()
        os.fsync(stream.fileno())
    expected = contracts.digest_bytes(target.path.read_bytes())

    repaired = target.repair_torn_tail(expected_digest=expected)

    assert repaired["structural_classification"] in {
        "truncated_json",
        "unterminated_string",
    }
    assert target.verify()["repair_history_count"] == 1


@pytest.mark.parametrize(
    "malformed_line",
    [
        b'{"sequence":2,"payload":"unterminated}\n',
        b'{"sequence":2,"payload":"bad\\q"}\n',
        b'{"sequence":2,"payload":{"nested":[1,2}}\n',
    ],
)
def test_mid_file_malformation_refuses_tail_repair(
    tmp_path: Path,
    malformed_line: bytes,
) -> None:
    target = delegation_ledger.RunLedger(
        tmp_path / contracts.digest_bytes(malformed_line)[-12:], "run-1"
    )
    append_event(target)
    with target.path.open("ab") as stream:
        stream.write(malformed_line)
        stream.write(b'{"sequence":3,"event_id":"terminal-torn')
        stream.flush()
        os.fsync(stream.fileno())
    expected = contracts.digest_bytes(target.path.read_bytes())
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError, match="prefix is corrupt"):
        target.repair_torn_tail(expected_digest=expected)
    assert target.path.read_bytes() == before


@pytest.mark.parametrize(
    ("tail", "classification"),
    [
        (
            b'{"sequence":2,"payload":',
            "truncated_json",
        ),
        (
            b'{"sequence":2,"payload":{"note":"torn',
            "unterminated_string",
        ),
        (
            b'{"sequence":2,"payload":{"note":"'
            + "\u20ac".encode("utf-8")[:2],
            "truncated_utf8_codepoint",
        ),
        (
            b'{"sequence":2,"payload":'
            + (b"[" * contracts.MAX_JSON_DEPTH),
            "truncated_json",
        ),
        (
            b'{"sequence":2,"payload":'
            + str(contracts.MAX_INTEGER).encode("ascii"),
            "truncated_json",
        ),
    ],
)
def test_genuine_terminal_truncation_and_v2_boundaries_remain_repairable(
    tmp_path: Path,
    tail: bytes,
    classification: str,
) -> None:
    target = delegation_ledger.RunLedger(
        tmp_path / contracts.digest_bytes(tail)[-12:], "run-1"
    )
    append_event(target)
    valid_prefix = target.path.read_bytes()
    with target.path.open("ab") as stream:
        stream.write(tail)
    expected = contracts.digest_bytes(target.path.read_bytes())

    repaired = target.repair_torn_tail(expected_digest=expected)
    assert repaired["structural_classification"] == classification
    assert target.path.read_bytes().startswith(valid_prefix)
    assert target.path.read_bytes() != valid_prefix
    assert target.read_records()[-1]["event_type"] == (
        delegation_ledger.REPAIR_EVENT_TYPE
    )
    assert target.verify()["valid"] is True


def test_malformed_existing_repair_intent_blocks_manual_recovery(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected_digest = add_torn_tail(target)
    target.intent_directory.mkdir(parents=True)
    (target.intent_directory / "bad.json").write_text(
        '{"schema_version":2}\n', encoding="utf-8"
    )
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError, match="malformed"):
        target.repair_torn_tail(expected_digest=expected_digest)
    assert target.path.read_bytes() == before


def test_v1_repair_intent_is_explicitly_refused(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected_digest = add_torn_tail(target)
    target.intent_directory.mkdir(parents=True)
    (target.intent_directory / "v1.json").write_text(
        '{"schema_version":1}\n', encoding="utf-8"
    )

    with pytest.raises(delegation_ledger.LedgerError, match="malformed"):
        target.repair_torn_tail(expected_digest=expected_digest)


def _persist_intent(target: delegation_ledger.RunLedger, value: dict) -> None:
    value["intent_digest"] = delegation_ledger._intent_digest(value)
    path = target.intent_directory / (
        value["before_digest"].split(":", 1)[1] + ".json"
    )
    path.write_bytes(
        contracts.canonical_json(value).encode("utf-8") + b"\n"
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("valid_prefix_byte_count", 0),
        ("valid_prefix_record_count", 0),
        ("intent_id", "repair-" + ("0" * 64)),
        ("candidate_repaired_digest", "sha256:" + ("1" * 64)),
        ("candidate_byte_count", 1),
        ("candidate_record_count", 1),
        ("candidate_last_record_digest", "sha256:" + ("3" * 64)),
        ("discarded_tail_digest", "sha256:" + ("2" * 64)),
        ("discarded_tail_byte_count", 1),
        ("structural_classification", "truncated_json"),
        ("extractable_sequence", None),
    ],
)
def test_repair_intent_relations_are_recomputed_from_before_bytes(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path / field, "run-repair")
    expected = add_torn_tail(target)
    with pytest.raises(delegation_ledger.RepairInterrupted):
        target.repair_torn_tail(
            expected_digest=expected,
            _fault_after="post_intent",
        )
    intent_path = next(target.intent_directory.glob("*.json"))
    intent = contracts.strict_json_loads(
        intent_path.read_text(encoding="utf-8")
    )
    assert isinstance(intent, dict)
    if field == "valid_prefix_record_count":
        intent["last_valid_record_digest"] = None
    intent[field] = replacement
    _persist_intent(target, intent)
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError):
        target.repair_torn_tail(expected_digest=expected)
    assert target.path.read_bytes() == before


def test_every_existing_repair_intent_must_relate_to_current_bytes(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected = add_torn_tail(target)
    with pytest.raises(delegation_ledger.RepairInterrupted):
        target.repair_torn_tail(
            expected_digest=expected,
            _fault_after="post_intent",
        )
    original_path = next(target.intent_directory.glob("*.json"))
    conflicting = contracts.strict_json_loads(
        original_path.read_text(encoding="utf-8")
    )
    assert isinstance(conflicting, dict)
    conflicting["before_digest"] = "sha256:" + ("0" * 64)
    _persist_intent(target, conflicting)
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError):
        target.repair_torn_tail(expected_digest=expected)
    assert target.path.read_bytes() == before


def test_repair_candidate_and_quarantine_are_relationally_verified(
    tmp_path: Path,
) -> None:
    candidate_target = delegation_ledger.RunLedger(
        tmp_path / "candidate", "run-repair"
    )
    candidate_expected = add_torn_tail(candidate_target)
    with pytest.raises(delegation_ledger.RepairInterrupted):
        candidate_target.repair_torn_tail(
            expected_digest=candidate_expected,
            _fault_after="post_candidate",
        )
    candidate_path = next(
        candidate_target.directory.glob("events.repair-*.candidate")
    )
    candidate_path.write_bytes(candidate_path.read_bytes() + b"x")
    before = candidate_target.path.read_bytes()
    with pytest.raises(delegation_ledger.LedgerError, match="candidate"):
        candidate_target.repair_torn_tail(
            expected_digest=candidate_expected
        )
    assert candidate_target.path.read_bytes() == before

    quarantine_target = delegation_ledger.RunLedger(
        tmp_path / "quarantine", "run-repair"
    )
    quarantine_expected = add_torn_tail(quarantine_target)
    with pytest.raises(delegation_ledger.RepairInterrupted):
        quarantine_target.repair_torn_tail(
            expected_digest=quarantine_expected,
            quarantine=True,
            _fault_after="post_quarantine",
        )
    quarantine_path = next(
        quarantine_target.quarantine_directory.glob("*.bin")
    )
    quarantine_path.write_bytes(b"conflicting")
    before = quarantine_target.path.read_bytes()
    with pytest.raises(delegation_ledger.LedgerError, match="quarantine"):
        quarantine_target.repair_torn_tail(
            expected_digest=quarantine_expected,
            quarantine=True,
        )
    assert quarantine_target.path.read_bytes() == before


def test_repair_marker_tamper_is_rejected_against_external_intent(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected = add_torn_tail(target)
    target.repair_torn_tail(expected_digest=expected)
    lines = target.path.read_bytes().splitlines(keepends=True)
    marker = contracts.strict_json_loads(lines[-1][:-1].decode("utf-8"))
    assert isinstance(marker, dict)
    assert isinstance(marker["payload"], dict)
    marker["payload"]["structural_classification"] = "truncated_json"
    unsigned = dict(marker)
    unsigned.pop("record_digest")
    marker["record_digest"] = contracts.digest_json(unsigned)
    lines[-1] = contracts.canonical_json(marker).encode("utf-8") + b"\n"
    target.path.write_bytes(b"".join(lines))
    assert target.verify()["valid"] is True
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError, match="candidate"):
        target.repair_torn_tail(expected_digest=expected)
    assert target.path.read_bytes() == before


def test_completed_quarantine_is_required_and_later_appends_are_verified(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected = add_torn_tail(target)
    repaired = target.repair_torn_tail(
        expected_digest=expected,
        quarantine=True,
    )
    assert repaired["status"] == "repaired"
    append_event(target, 2)
    replay = target.repair_torn_tail(
        expected_digest=expected,
        quarantine=True,
    )
    assert replay["status"] == "completed_replay"

    quarantine_path = next(target.quarantine_directory.glob("*.bin"))
    quarantine_path.unlink()
    before = target.path.read_bytes()
    with pytest.raises(
        delegation_ledger.LedgerError,
        match="quarantine is required",
    ):
        target.repair_torn_tail(
            expected_digest=expected,
            quarantine=True,
        )
    assert target.path.read_bytes() == before


def test_later_noncanonical_stream_blocks_completed_repair_replay(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected = add_torn_tail(target)
    target.repair_torn_tail(expected_digest=expected)
    append_event(target, 2)
    lines = target.path.read_bytes().splitlines(keepends=True)
    target.path.write_bytes(lines[0] + lines[1] + b" " + lines[2])
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError, match="canonical valid"):
        target.repair_torn_tail(expected_digest=expected)
    assert target.path.read_bytes() == before


def _prebuilt_ledger_bytes(run_id: str, count: int) -> bytes:
    lines = []
    previous = None
    for sequence in range(1, count + 1):
        event = {
            "schema_version": contracts.SCHEMA_VERSION,
            "sequence": sequence,
            "event_id": "event-{}".format(sequence),
            "run_id": run_id,
            "event_type": "capacity_sample",
            "recorded_at": NOW,
            "delegation_id": None,
            "task_id": None,
            "runtime_status": "completed",
            "payload": {"number": sequence},
            "previous_record_digest": previous,
        }
        event["record_digest"] = contracts.digest_json(event)
        previous = event["record_digest"]
        lines.append(contracts.canonical_json(event).encode("utf-8") + b"\n")
    return b"".join(lines)


def test_prebuilt_capacity_sample_full_verification_fits_lock_budget(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "capacity-run")
    target.directory.mkdir(parents=True)
    data = _prebuilt_ledger_bytes(target.run_id, delegation_ledger.MAX_RECORDS)
    assert len(data) <= delegation_ledger.MAX_LEDGER_BYTES
    target.path.write_bytes(data)

    started = time.perf_counter()
    report = target.verify()
    elapsed = time.perf_counter() - started

    assert report["valid"] is True
    assert report["record_count"] == delegation_ledger.MAX_RECORDS
    assert elapsed < delegation_ledger.DEFAULT_LOCK_TIMEOUT_S


def test_repair_marker_can_fill_the_final_record_capacity(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "capacity-repair")
    target.directory.mkdir(parents=True)
    prefix = _prebuilt_ledger_bytes(
        target.run_id, delegation_ledger.MAX_RECORDS - 1
    )
    tail = b'{"sequence":10000,"payload":'
    target.path.write_bytes(prefix + tail)
    expected = contracts.digest_bytes(target.path.read_bytes())

    repaired = target.repair_torn_tail(expected_digest=expected)

    assert repaired["status"] == "repaired"
    report = target.verify()
    assert report["valid"] is True
    assert report["record_count"] == delegation_ledger.MAX_RECORDS
    assert report["repair_history_count"] == 1
    assert target.read_records()[-1]["sequence"] == delegation_ledger.MAX_RECORDS
    with pytest.raises(delegation_ledger.LedgerError, match="record bound"):
        append_event(target, delegation_ledger.MAX_RECORDS + 1)


def test_sequential_append_timing_is_observational_not_a_correctness_gate(
    tmp_path: Path,
    record_property,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "sequential-run")
    started = time.perf_counter()
    for number in range(1, 51):
        append_event(target, number)
    elapsed = time.perf_counter() - started
    record_property("sequential_append_50_seconds", elapsed)

    assert target.verify()["record_count"] == 50
