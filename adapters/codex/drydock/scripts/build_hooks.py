#!/usr/bin/env python3
"""Build Drydock's deterministic Codex runtime, manifest, and hook definition."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path


HEADER = (
    "# DRYDOCK CODEX HOOK RUNTIME v1\n"
    "# Generated deterministically from scripts/hook_runtime_source.py.\n"
    "# Do not edit: run scripts/build_hooks.py.\n\n"
)
RUNTIME_NAME = "runtime.py"
MANIFEST_NAME = "runtime.manifest.json"
HOOKS_NAME = "hooks.json"
ALLOWED_HOOK_FILES = {RUNTIME_NAME, MANIFEST_NAME, HOOKS_NAME}


def _normalized_source(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("hook runtime source must not contain a BOM")
    text = raw.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    return text


def runtime_bytes(source: Path) -> bytes:
    return (HEADER + _normalized_source(source)).encode("utf-8")


def _verifier_source(digest: str) -> str:
    return f"""import hashlib,io,json,os,sys,sysconfig
EXPECTED={digest!r}
NAME={RUNTIME_NAME!r}
def fail():
 raw=getattr(sys,'stdin').read()
 try: event=(json.loads(raw) or {{}}).get('hook_event_name')
 except BaseException: event=None
 if event=='PreToolUse':
  out={{'hookSpecificOutput':{{'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':'Drydock guard unavailable: runtime integrity verification failed.'}}}}
 else:
  out={{'systemMessage':'Drydock guard unavailable: runtime integrity verification failed.'}}
 print(json.dumps(out,separators=(',',':'),sort_keys=True));sys.stdout.flush()
try:
 original=sys.stdin.read()
 root=os.environ.get('PLUGIN_ROOT') or os.environ.get('CLAUDE_PLUGIN_ROOT')
 if not root or not os.path.isabs(root): raise RuntimeError()
 hooks=os.path.realpath(os.path.join(root,'hooks'))
 names=sorted(name for name in os.listdir(hooks) if name.endswith('.py'))
 if names!=[NAME]: raise RuntimeError()
 path=os.path.join(hooks,NAME)
 with open(path,'rb') as stream: captured=stream.read()
 if hashlib.sha256(captured).hexdigest()!=EXPECTED: raise RuntimeError()
 if captured.startswith(b'\\xef\\xbb\\xbf') or b'\\r' in captured: raise RuntimeError()
 if not captured.startswith(b'# DRYDOCK CODEX HOOK RUNTIME v1\\n'): raise RuntimeError()
 roots=[]
 for key in ('stdlib','platstdlib'):
  value=sysconfig.get_path(key)
  if value:
   value=os.path.realpath(value)
   if value not in roots: roots.append(value)
 if not roots or any(os.path.commonpath([hooks,value])==hooks for value in roots): raise RuntimeError()
 sys.path[:]=roots
 sys.stdin=io.TextIOWrapper(io.BytesIO(original.encode('utf-8')),encoding='utf-8')
 scope={{'__name__':'__main__','__file__':'<verified-drydock-runtime>','DRYDOCK_RUNTIME_SHA256':EXPECTED}}
 exec(compile(captured,'<verified-drydock-runtime>','exec'),scope,scope)
except BaseException:
 try: sys.stdin=io.StringIO(locals().get('original',''))
 except BaseException: pass
 fail()
"""


def _command(verifier: str, windows: bool) -> str:
    encoded = base64.b64encode(verifier.encode("utf-8")).decode("ascii")
    launcher = "py -3" if windows else "python3"
    bootstrap = (
        "import base64;"
        "exec(compile(base64.b64decode('"
        + encoded
        + "'),'<drydock-inline-verifier>','exec'))"
    )
    return f'{launcher} -I -S -c "{bootstrap}"'


def build_outputs(source: Path) -> dict[str, bytes]:
    runtime = runtime_bytes(source)
    digest = hashlib.sha256(runtime).hexdigest()
    verifier = _verifier_source(digest)
    handler = {
        "type": "command",
        "command": _command(verifier, windows=False),
        "commandWindows": _command(verifier, windows=True),
        "timeout": 15,
        "statusMessage": "Checking Drydock guardrails",
    }
    hooks = {
        "description": (
            "Drydock non-managed conditional guardrails; "
            f"runtime-sha256={digest}"
        ),
        "hooks": {
            "PreToolUse": [
                {"matcher": "^Bash$", "hooks": [handler]},
                {"matcher": "^apply_patch$", "hooks": [handler]},
            ],
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear|compact",
                    "hooks": [handler],
                }
            ],
            "Stop": [{"hooks": [handler]}],
        },
    }
    manifest = {
        "files": [{"path": RUNTIME_NAME, "sha256": digest}],
        "format": "plain-utf8-lf",
        "schema_version": 1,
        "source": "scripts/hook_runtime_source.py",
    }
    return {
        RUNTIME_NAME: runtime,
        MANIFEST_NAME: (
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
        HOOKS_NAME: (json.dumps(hooks, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    }


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


def verify_outputs(source: Path, output: Path) -> list[str]:
    expected = build_outputs(source)
    failures: list[str] = []
    actual_names = {path.name for path in output.iterdir()} if output.is_dir() else set()
    unexpected_python = {
        name for name in actual_names if name.endswith(".py")
    } - {RUNTIME_NAME}
    if unexpected_python:
        failures.append(
            "unexpected executable hook files: " + ", ".join(sorted(unexpected_python))
        )
    for name, content in expected.items():
        path = output / name
        if not path.is_file():
            failures.append(f"missing generated hook file: {name}")
        elif path.read_bytes() != content:
            failures.append(f"generated hook drift: {name}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        failures = verify_outputs(args.source, args.output)
        if failures:
            for failure in failures:
                print(failure)
            return 1
        print(f"hook runtime and definition match source: {args.output}")
        return 0

    outputs = build_outputs(args.source)
    for name, content in outputs.items():
        _write_atomic(args.output / name, content)
    digest = json.loads(outputs[MANIFEST_NAME])["files"][0]["sha256"]
    print(f"wrote verified hook runtime {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
