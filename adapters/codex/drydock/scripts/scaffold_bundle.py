#!/usr/bin/env python3
"""Build and verify Drydock's deterministic project-scaffold bundle.

The repository's ``assets/project-scaffold`` tree is authoritative. The Codex
plugin carries one generated JSON bundle so it can initialize another
repository without a second Drydock installation. Every entry is content
addressed and validated before use.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


SCHEMA_VERSION = 1
MAX_FILES = 512
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
EXCLUDED_PATHS = frozenset(
    {
        "CLAUDE.md",
        ".codex/hooks.json",
        ".codex/hooks/drydock_guard.py",
    }
)


class BundleError(ValueError):
    """Raised when a scaffold source or bundle violates its contract."""


@dataclass(frozen=True)
class BundleEntry:
    path: str
    sha256: str
    content: bytes


def _normalized_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BundleError("bundle paths must be non-empty POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BundleError(f"unsafe bundle path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise BundleError(f"non-canonical bundle path: {value!r}")
    return normalized


def _tree_digest(entries: Iterable[BundleEntry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(entry.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry.sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def collect_source(source: Path) -> list[BundleEntry]:
    """Collect an allowlisted, deterministic view of a scaffold source tree."""
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise BundleError(f"scaffold source is not a directory: {source}")

    paths: list[Path] = []
    for current, directories, files in os.walk(source, followlinks=False):
        current_path = Path(current)
        for name in [*directories, *files]:
            candidate = current_path / name
            if candidate.is_symlink():
                raise BundleError(f"symlinks are not allowed in scaffold source: {candidate}")
        for name in files:
            candidate = current_path / name
            relative = candidate.relative_to(source).as_posix()
            if relative not in EXCLUDED_PATHS:
                paths.append(candidate)

    if len(paths) > MAX_FILES:
        raise BundleError(f"scaffold contains more than {MAX_FILES} files")

    entries: list[BundleEntry] = []
    total = 0
    for path in sorted(paths, key=lambda item: item.relative_to(source).as_posix()):
        relative = _normalized_path(path.relative_to(source).as_posix())
        content = path.read_bytes()
        if len(content) > MAX_FILE_BYTES:
            raise BundleError(f"scaffold file exceeds size limit: {relative}")
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise BundleError("scaffold exceeds total size limit")
        entries.append(
            BundleEntry(
                path=relative,
                sha256=hashlib.sha256(content).hexdigest(),
                content=content,
            )
        )
    return entries


def build_bundle_bytes(source: Path) -> bytes:
    entries = collect_source(source)
    document = {
        "entries": [
            {
                "content_b64": base64.b64encode(entry.content).decode("ascii"),
                "path": entry.path,
                "sha256": entry.sha256,
            }
            for entry in entries
        ],
        "excluded_paths": sorted(EXCLUDED_PATHS),
        "schema_version": SCHEMA_VERSION,
        "source": "assets/project-scaffold",
        "source_tree_sha256": _tree_digest(entries),
    }
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def load_bundle_bytes(raw: bytes) -> list[BundleEntry]:
    """Validate raw bundle bytes and return verified entries."""
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleError(f"bundle is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise BundleError("bundle root must be an object")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise BundleError("unsupported bundle schema")
    if document.get("source") != "assets/project-scaffold":
        raise BundleError("unexpected bundle source")
    if document.get("excluded_paths") != sorted(EXCLUDED_PATHS):
        raise BundleError("unexpected bundle exclusions")
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list) or len(raw_entries) > MAX_FILES:
        raise BundleError("bundle entries must be a bounded list")

    entries: list[BundleEntry] = []
    seen: set[str] = set()
    total = 0
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or set(raw_entry) != {
            "content_b64",
            "path",
            "sha256",
        }:
            raise BundleError("bundle entry has an invalid shape")
        path = _normalized_path(raw_entry["path"])
        if path in seen:
            raise BundleError(f"duplicate bundle path: {path}")
        seen.add(path)
        declared_digest = raw_entry["sha256"]
        if (
            not isinstance(declared_digest, str)
            or len(declared_digest) != 64
            or any(char not in "0123456789abcdef" for char in declared_digest)
        ):
            raise BundleError(f"invalid digest for {path}")
        try:
            content = base64.b64decode(raw_entry["content_b64"], validate=True)
        except (TypeError, ValueError) as exc:
            raise BundleError(f"invalid base64 for {path}") from exc
        if len(content) > MAX_FILE_BYTES:
            raise BundleError(f"bundle file exceeds size limit: {path}")
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise BundleError("bundle exceeds total size limit")
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != declared_digest:
            raise BundleError(f"digest mismatch for {path}")
        entries.append(BundleEntry(path, declared_digest, content))

    if [entry.path for entry in entries] != sorted(entry.path for entry in entries):
        raise BundleError("bundle entries are not sorted")
    if document.get("source_tree_sha256") != _tree_digest(entries):
        raise BundleError("bundle tree digest mismatch")
    return entries


def load_bundle(path: Path) -> list[BundleEntry]:
    return load_bundle_bytes(path.read_bytes())


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare the exact deterministic bytes without writing",
    )
    args = parser.parse_args(argv)

    expected = build_bundle_bytes(args.source)
    if args.check:
        if not args.output.is_file():
            print(f"bundle missing: {args.output}")
            return 1
        actual = args.output.read_bytes()
        if actual != expected:
            print(f"bundle drift: {args.output}")
            return 1
        load_bundle_bytes(actual)
        print(f"bundle matches source: {args.output}")
        return 0

    _write_atomic(args.output, expected)
    entries = load_bundle_bytes(expected)
    print(f"wrote {len(entries)} verified scaffold files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
