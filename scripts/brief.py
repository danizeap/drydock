#!/usr/bin/env python3
"""Drydock Owner-brief engine: deterministic FACTS about project state.

Plugin-only (no scaffold copy, no check_sync pair — ships and updates with the
plugin uniformly). Three modes:

  python brief.py                      -> print the FACTS block (JSON) to stdout
  python brief.py --write-status       -> also author OWNER_STATUS.md (frozen
                                          per-language templates; deterministic
                                          bytes; atomic; no-op when unchanged)
  python brief.py --record-verify NAME -> re-run the deterministic packet gate;
                                          on a genuine pass, record a verify-run
                                          ledger event binding the packet's
                                          current content-hash

Design contract (red-team-derived, spec-pinned):
- Rungs, counts, provenance, and availability are assigned ONLY here, by code.
  The model that renders the chat brief may translate the FACTS block; it may
  never add to it. Absence renders as "unavailable", never as zero.
- Ascent requires positive evidence. This engine deliberately does NOT reuse
  the completion gate's claimed-done parsers: those fail toward silence, which
  for the brief's polarity would fail toward false peace (live-confirmed:
  a missing tasks.md reads as claimed-done; a "NOT VERIFIED" Result reads as
  "filled"). Here a packet with no checkboxes is an idea; the checked rung
  requires an affirmative PASS grammar; NOT VERIFIED / BLOCKED / headingless
  freeze at built-not-checked.
- "Independently" is never rendered from typeable repo text. The strongest
  caption ("confirmed on this computer") is earned only by a verify-run ledger
  event whose content-hash matches the packet's CURRENT hash.
- The module import is anchored to THIS file's plugin location — never cwd,
  never the project tree — so a hostile repo cannot plant a decoy
  _drydock_common.py and a scaffolded project's stale copy cannot skew paths.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(_HOOKS))
from _drydock_common import (PREVENTION_CATEGORIES, append_event, find_drydock_root,  # noqa: E402
                             fingerprint_project, ledger_path, plugin_root_from_env,
                             project_fingerprint_hex, read_events, read_head)

ENGINE_VERSION = 1
_MAX_ITEMS = 30
_SENTENCE = re.compile(r"(.+?[.!?])(\s|$)")

# Frozen status-file vocabulary. Deterministic bytes are the point: the durable
# artifact must be golden-testable and impossible for a model to embellish.
LABELS = {
    "en": {
        "title": "Project status",
        "stale": "Snapshot generated {date} - anything after this date is NOT reflected. Ask for a fresh brief (/drydock:brief).",
        "commit": "As of commit {head}.",
        "commit_unavailable": "As of commit: unavailable.",
        "attention": "Needs you",
        "nothing": "Nothing needs you - checked: work items, verification records, archive records, safety-net history.",
        "in_flight": "In flight",
        "shipped": "Shipped",
        "none_in_flight": "(nothing in flight)",
        "none_shipped": "(nothing shipped yet)",
        "safety": "Safety net",
        "goal_prefix": "Goal:",
        "your_move": "Your move:",
        "as_of": "as of {date}",
        "rung": {
            "idea": "an idea - not being built yet",
            "being-built": "being built ({done} of {total} steps done)",
            "built-not-checked": "built, but NOT yet checked",
            "checked-recorded": "checked & recorded (per this project's own records)",
            "done-documented": "done & documented ({date})",
            "archived-exceptions": "closed out WITH recorded exceptions",
            "incomplete-record": "archive record incomplete - treat as unknown",
        },
        "say": {
            "idea": "Safe to say: \"we're considering it\" - nothing more.",
            "being-built": "Safe to say: \"it's in progress\" - do not promise a date yet.",
            "built-not-checked": "Safe to say: \"it's built, being checked\" - NOT \"it's done\".",
            "checked-recorded": "Safe to say: \"it works, checks passed\" ({asof}).",
            "done-documented": "Safe to say: \"it's done and documented\" ({asof}).",
            "archived-exceptions": "Do not promise this works until you review the exceptions.",
            "incomplete-record": "Do not make promises based on this item.",
        },
        "confirmed_here": "confirmed on this computer",
        "not_confirmed_here": "not re-confirmed on this computer",
        "record_not_pass": "a verification record exists but it is not a pass",
        "exceptions_move": "review the recorded exceptions: accept them or reopen the work",
        "sessions": "Guardrails checked live at every session start. Coverage here: {n} session(s) on this computer since {date}.",
        "history_unavailable": "Safety-net history: unavailable on this computer.",
        "paused_none": "No actions needed pausing in this window.",
        "paused": "Paused {n} action(s) until a change plan existed (since {date}).",
        "paused_note": "Pauses are recoverable - the work continues governed after a plan exists; occasionally a pause is a false alarm, which costs a retry, not lost work.",
        "older_history": "History from other computers or earlier dates is not visible here.",
        "not_initialized": "This folder is not set up with Drydock.",
        "footer": "Everything above is read from the project's own records by deterministic code. Anything unreadable says so - it is never shown as fine.",
    },
    "es": {
        "title": "Estado del proyecto",
        "stale": "Instantanea generada el {date} - nada posterior a esa fecha aparece aqui. Pide un resumen nuevo (/drydock:brief).",
        "commit": "A fecha del commit {head}.",
        "commit_unavailable": "Commit: no disponible.",
        "attention": "Te necesita",
        "nothing": "Nada te necesita - revisado: trabajos activos, registros de verificacion, registros de archivo, historial de la red de seguridad.",
        "in_flight": "En curso",
        "shipped": "Entregado",
        "none_in_flight": "(nada en curso)",
        "none_shipped": "(nada entregado todavia)",
        "safety": "Red de seguridad",
        "goal_prefix": "Objetivo:",
        "your_move": "Te toca:",
        "as_of": "a fecha {date}",
        "rung": {
            "idea": "una idea - todavia no se construye",
            "being-built": "en construccion ({done} de {total} pasos hechos)",
            "built-not-checked": "construido, pero AUN sin comprobar",
            "checked-recorded": "comprobado y registrado (segun los registros del propio proyecto)",
            "done-documented": "terminado y documentado ({date})",
            "archived-exceptions": "cerrado CON excepciones registradas",
            "incomplete-record": "registro de archivo incompleto - tratar como desconocido",
        },
        "say": {
            "idea": "Puedes decir: \"lo estamos valorando\" - nada mas.",
            "being-built": "Puedes decir: \"esta en marcha\" - no prometas fechas todavia.",
            "built-not-checked": "Puedes decir: \"esta construido y en revision\" - NO \"esta terminado\".",
            "checked-recorded": "Puedes decir: \"funciona, paso las comprobaciones\" ({asof}).",
            "done-documented": "Puedes decir: \"esta terminado y documentado\" ({asof}).",
            "archived-exceptions": "No prometas que funciona hasta revisar las excepciones.",
            "incomplete-record": "No hagas promesas basadas en este elemento.",
        },
        "confirmed_here": "confirmado en este ordenador",
        "not_confirmed_here": "sin reconfirmar en este ordenador",
        "record_not_pass": "existe un registro de verificacion pero no es un aprobado",
        "exceptions_move": "revisa las excepciones registradas: aceptalas o reabre el trabajo",
        "sessions": "Las barreras se comprueban en vivo al inicio de cada sesion. Cobertura aqui: {n} sesion(es) en este ordenador desde {date}.",
        "history_unavailable": "Historial de la red de seguridad: no disponible en este ordenador.",
        "paused_none": "Ninguna accion necesito pausa en esta ventana.",
        "paused": "Pauso {n} accion(es) hasta que existiera un plan de cambio (desde {date}).",
        "paused_note": "Las pausas son recuperables - el trabajo continua gobernado cuando existe un plan; a veces una pausa es una falsa alarma, que cuesta un reintento, no trabajo perdido.",
        "older_history": "El historial de otros ordenadores o fechas anteriores no es visible aqui.",
        "not_initialized": "Esta carpeta no esta configurada con Drydock.",
        "footer": "Todo lo anterior lo lee codigo deterministico de los registros del propio proyecto. Lo que no se puede leer se dice - nunca se muestra como correcto.",
    },
}


def _today():
    import time
    return time.strftime("%Y-%m-%d")


def _first_sentence(text):
    text = re.sub(r"[*_`]", "", " ".join(text.split()))
    m = _SENTENCE.match(text)
    return (m.group(1) if m else text)[:240]


def _section(text, heading):
    """Body of a '## <heading>' section (up to the next ## heading), or ''."""
    m = re.search(r"(?im)^##\s+" + re.escape(heading) + r"\s*$(.*?)(?=^##\s|\Z)",
                  text, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _goal_line(brief_text):
    """Owner-language line: the 'What this means for your product' section if
    present, else the User Need first paragraph. One sentence, engine-truncated
    (enthusiasm cannot compound past a period)."""
    for heading in ("What this means for your product", "User Need"):
        body = _section(brief_text, heading)
        if body:
            para = body.split("\n\n")[0].strip()
            if para:
                return _first_sentence(para)
    return ""


_PASS_LINE = re.compile(r"^pass\b")
_NEGATIVE = re.compile(r"^(not\b|no\b|fail|blocked)")


def _result_verdict(verif_text):
    """'pass' | 'not-pass' | 'missing'. Own parser, opposite polarity from the
    completion gate's: only an affirmative first line of an explicit '## Result'
    section counts. Headingless, empty, negative, or weird all refuse ascent."""
    if not verif_text.strip():
        return "missing"
    body = _section(verif_text, "Result")
    if not body:
        return "missing"
    first = body.splitlines()[0].strip().strip("*_`").casefold()
    if first.startswith("pending"):
        return "missing"
    if _PASS_LINE.match(first) and not _NEGATIVE.match(first):
        return "pass"
    return "not-pass"


def _task_counts(tasks_text):
    checked = len(re.findall(r"(?m)^\s*-\s*\[[xX]\]\s+", tasks_text))
    unchecked = re.findall(r"(?m)^\s*-\s*\[\s\]\s+(.*)$", tasks_text)
    non_verif = [u for u in unchecked if not re.search(r"verif", u, re.IGNORECASE)]
    return checked, len(unchecked), len(non_verif)


def _safe_name(raw):
    return re.sub(r"[<>`]", "", raw)[:64]


def _active_item(pkg_dir, verify_runs):
    name = _safe_name(pkg_dir.name)
    brief_text = read_head(pkg_dir / "brief.md")
    tasks_path = pkg_dir / "tasks.md"
    tasks_text = read_head(tasks_path) if tasks_path.is_file() else ""
    checked, unchecked, non_verif = _task_counts(tasks_text)
    item = {"name": name, "goal": _goal_line(brief_text), "kind": "active",
            "counts": {"done": checked, "pending": unchecked}}
    if not tasks_path.is_file() or (checked + unchecked) == 0:
        item["rung"] = "idea"          # ascent requires positive evidence
        return item
    if non_verif > 0 or checked == 0:
        item["rung"] = "being-built"
        return item
    verdict = _result_verdict(read_head(pkg_dir / "verification.md")
                              if (pkg_dir / "verification.md").is_file() else "")
    if verdict == "pass":
        item["rung"] = "checked-recorded"
        root = pkg_dir.parent.parent.parent  # <root>/sdd-plus/changes/<name>
        cur = fingerprint_project(root).get(pkg_dir.name, {}).get("hash")
        item["confirmed_here"] = bool(cur and cur in verify_runs.get(pkg_dir.name, set()))
    else:
        item["rung"] = "built-not-checked"
        if verdict == "not-pass":
            item["note"] = "record-not-pass"
            item["your_move"] = "review-not-pass"
    return item


def _archive_item(arch_dir):
    name = _safe_name(arch_dir.name)
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", name)
    date, label = (m.group(1), m.group(2)) if m else (None, name)
    required = ("brief.md", "tasks.md", "verification.md", "decision-log.md")
    missing = [f for f in required if not (arch_dir / f).is_file()]
    item = {"name": label, "kind": "archived", "date": date,
            "goal": _goal_line(read_head(arch_dir / "brief.md"))}
    if missing or date is None:
        item["rung"] = "incomplete-record"   # hand-moved decoys earn no rung
        return item
    overridden = bool(re.search(r"(?im)^##\s+Override\b",
                                read_head(arch_dir / "decision-log.md")))
    verdict = _result_verdict(read_head(arch_dir / "verification.md"))
    if overridden or verdict != "pass":
        item["rung"] = "archived-exceptions"  # --force waivers stay visible
        item["your_move"] = "review-exceptions"
    else:
        item["rung"] = "done-documented"
    return item


def _git_head(root):
    """Short HEAD sha via stdlib file reads (no subprocess). 'unavailable' on any doubt."""
    try:
        git = root / ".git"
        if git.is_file():  # worktree: 'gitdir: <path>'
            m = re.match(r"gitdir:\s*(.+)", read_head(git).strip())
            if not m:
                return "unavailable"
            git = Path(m.group(1)) if os.path.isabs(m.group(1)) else (root / m.group(1))
        head = read_head(git / "HEAD").strip()
        if head.startswith("ref:"):
            ref = head.split(None, 1)[1].strip()
            direct = git / ref
            if direct.is_file():
                return read_head(direct).strip()[:7] or "unavailable"
            for line in read_head(git / "packed-refs").splitlines():
                if line.strip().endswith(" " + ref) and not line.startswith("#"):
                    return line.split()[0][:7]
            return "unavailable"
        return head[:7] if re.match(r"^[0-9a-f]{7,}", head) else "unavailable"
    except BaseException:
        return "unavailable"


def _context_state(root):
    ctx = root / "PROJECT_CONTEXT.md"
    if not ctx.is_file():
        return "missing"
    text = read_head(ctx)
    if len(re.findall(r"(?mi)^\s*-?\s*TBD\s*$", text)) >= 3 or "Copy this file" in text:
        return "template"
    return "real"


def _project_birth(root, oldest_archive_date):
    """Best-effort earliest date this project plausibly existed at this path:
    the older of the stable scaffold anchors' mtimes, lowered by the oldest
    archive date (which travels with git). Used to exclude a DEAD project's
    ledger events when an unrelated project lands on a recycled path — the
    exclusion direction is honest (history shrinks and says so; it never
    inflates)."""
    import time
    stamps = []
    for rel in ("AGENTS.md", "sdd-plus", "PROJECT_CONTEXT.md"):
        try:
            stamps.append((root / rel).stat().st_mtime)
        except OSError:
            continue
    dates = []
    if stamps:
        try:
            dates.append(time.strftime("%Y-%m-%d", time.localtime(min(stamps))))
        except (OSError, OverflowError, ValueError):
            pass
    if oldest_archive_date:
        dates.append(oldest_archive_date)
    return min(dates) if dates else None


def facts(root):
    """The FACTS block. Every value here is deterministic; unreadable sources
    surface as 'unavailable' (never zero, never omitted)."""
    if root is None:
        return {"drydock": "not-initialized", "engine": ENGINE_VERSION, "generated": _today()}

    items = []
    changes = root / "sdd-plus" / "changes"
    try:
        active = sorted(p for p in changes.iterdir() if p.is_dir()) if changes.is_dir() else []
    except OSError:
        active = []
    arch = root / "sdd-plus" / "archive"
    try:
        archived = sorted((p for p in arch.iterdir() if p.is_dir()),
                          key=lambda p: p.name, reverse=True) if arch.is_dir() else []
    except OSError:
        archived = []
    oldest_archive_date = None
    for p in sorted(archived, key=lambda p: p.name)[:1]:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-", p.name)
        oldest_archive_date = m.group(1) if m else None

    events = read_events(root)
    kept, excluded_older = [], False
    if events is not None:
        birth = _project_birth(root, oldest_archive_date)
        kept = [e for e in events if not birth or e.get("ts", "") >= birth]
        excluded_older = len(kept) < len(events)
    verify_runs = {}
    for e in kept:
        if e.get("category") == "verify-run" and isinstance(e.get("packet"), str):
            verify_runs.setdefault(e["packet"], set()).add(e.get("hash"))

    for p in active[:_MAX_ITEMS]:
        items.append(_active_item(p, verify_runs))
    for p in archived[:_MAX_ITEMS]:
        items.append(_archive_item(p))

    if events is None:
        guardrails = {"history": "unavailable"}
    else:
        # ledger-created is itself an event: if it survived the birth filter it is
        # kept[0], so the oldest kept ts is always the honest coverage bound.
        since = kept[0]["ts"] if kept else _today()
        older_not_visible = excluded_older or bool(
            oldest_archive_date and since > oldest_archive_date)
        sessions = sum(1 for e in kept if e.get("category") == "session")
        paused = {}
        for e in kept:
            c = e.get("category", "")
            if c in PREVENTION_CATEGORIES:
                paused[c] = paused.get(c, 0) + 1
        guardrails = {"history": "ok", "since": since, "sessions": sessions,
                      "paused": paused, "paused_total": sum(paused.values()),
                      "older_history_not_visible": older_not_visible}

    moves = []
    for it in items:
        if it.get("your_move"):
            moves.append({"item": it["name"], "move": it["your_move"]})
    return {
        "drydock": "ok",
        "engine": ENGINE_VERSION,
        "generated": _today(),
        "fingerprint": project_fingerprint_hex(root),
        "head": _git_head(root),
        "project_context": _context_state(root),
        "items": items,
        "your_move": moves,
        "guardrails": guardrails,
    }


# --- OWNER_STATUS.md rendering (deterministic; frozen labels) ----------------
def _render_item(it, L, generated):
    rung = it["rung"]
    tpl = L["rung"][rung]
    label = tpl.format(done=it.get("counts", {}).get("done", 0),
                       total=(it.get("counts", {}).get("done", 0)
                              + it.get("counts", {}).get("pending", 0)),
                       date=it.get("date") or "")
    asof = L["as_of"].format(date=generated)
    lines = [f"- **{it['name']}** - {label}"]
    if it.get("goal"):
        prefix = "" if rung == "done-documented" else L["goal_prefix"] + " "
        lines.append(f"  {prefix}{it['goal']}")
    lines.append("  " + L["say"][rung].format(asof=asof))
    if rung == "checked-recorded":
        lines.append("  (" + (L["confirmed_here"] if it.get("confirmed_here")
                              else L["not_confirmed_here"]) + ")")
    if it.get("note") == "record-not-pass":
        lines.append("  (" + L["record_not_pass"] + ")")
    if it.get("your_move") == "review-exceptions":
        lines.append("  " + L["your_move"] + " " + L["exceptions_move"])
    return lines


def render_status(f, lang):
    L = LABELS.get(lang) or LABELS["en"]
    g = f["generated"]
    out = [f"# {L['title']} - {g}", ""]
    out.append("**" + L["stale"].format(date=g) + "**")
    head = f.get("head", "unavailable")
    out.append(L["commit"].format(head=head) if head != "unavailable"
               else L["commit_unavailable"])
    out.append("")
    out.append(f"## {L['attention']}")
    if f["your_move"]:
        for mv in f["your_move"]:
            out.append(f"- **{mv['item']}**: " + L["your_move"] + " " +
                       (L["exceptions_move"] if mv["move"] == "review-exceptions"
                        else L["record_not_pass"]))
    else:
        out.append("- " + L["nothing"])
    out.append("")
    active = [i for i in f["items"] if i["kind"] == "active"]
    shipped = [i for i in f["items"] if i["kind"] == "archived"]
    out.append(f"## {L['in_flight']}")
    if active:
        for it in active:
            out.extend(_render_item(it, L, g))
    else:
        out.append(L["none_in_flight"])
    out.append("")
    out.append(f"## {L['shipped']}")
    if shipped:
        for it in shipped:
            out.extend(_render_item(it, L, g))
    else:
        out.append(L["none_shipped"])
    out.append("")
    out.append(f"## {L['safety']}")
    gr = f["guardrails"]
    if gr.get("history") != "ok":
        out.append("- " + L["history_unavailable"])
    else:
        out.append("- " + L["sessions"].format(n=gr["sessions"], date=gr["since"]))
        if gr["paused_total"]:
            out.append("- " + L["paused"].format(n=gr["paused_total"], date=gr["since"]))
        else:
            out.append("- " + L["paused_none"])
        out.append("  " + L["paused_note"])
        if gr.get("older_history_not_visible"):
            out.append("- " + L["older_history"])
    out.append("")
    out.append("*" + L["footer"] + "*")
    out.append("")
    out.append(f"<!-- drydock-brief fp={f['fingerprint']} lang={lang} v={ENGINE_VERSION} -->")
    return "\n".join(out) + "\n"


def _existing_meta(status_path):
    try:
        m = re.search(r"<!--\s*drydock-brief\s+fp=([0-9a-f]{16})\s+lang=(\w{2})",
                      read_head(status_path))
        return (m.group(1), m.group(2)) if m else (None, None)
    except BaseException:
        return None, None


def write_status(root, f, lang):
    """Author OWNER_STATUS.md atomically. Returns a result dict. No-op (and says
    so) when the embedded fingerprint+lang already match — a no-change brief must
    not churn the Owner's git diff."""
    if f.get("drydock") != "ok":
        return {"written": False, "reason": "not-initialized"}
    status = root / "OWNER_STATUS.md"
    old_fp, old_lang = _existing_meta(status) if status.is_file() else (None, None)
    if not lang:
        lang = old_lang or "en"
    if lang not in LABELS:
        lang = "en"
    if old_fp == f["fingerprint"] and old_lang == lang:
        return {"written": False, "reason": "unchanged", "lang": lang}
    content = render_status(f, lang)
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=str(root), prefix=".drydock-status-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp, str(status))
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return {"written": False, "reason": "write-failed"}
    return {"written": True, "lang": lang, "path": str(status)}


def record_verify(root, name):
    """Re-run the deterministic packet gate; only a genuine pass records the
    verify-run event (with the packet's CURRENT content-hash). Typing a PASS
    into verification.md cannot mint this — the gate itself must pass."""
    if root is None:
        return {"recorded": False, "reason": "not-initialized"}
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name or ""):
        return {"recorded": False, "reason": "bad-name"}
    sdd = root / "scripts" / "sdd.py"
    if not sdd.is_file():
        sdd = Path(__file__).resolve().parent / "sdd.py"
    try:
        proc = subprocess.run([sys.executable, str(sdd), "verify", name],
                              cwd=str(root), capture_output=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError):
        return {"recorded": False, "reason": "gate-unavailable"}
    if proc.returncode != 0:
        return {"recorded": False, "reason": "gate-failed",
                "detail": (proc.stdout or b"").decode("utf-8", "replace")[-400:]}
    cur = fingerprint_project(root).get(name, {}).get("hash")
    if not cur:
        return {"recorded": False, "reason": "packet-not-found"}
    append_event(root, "brief", "verify", "verify-run", extra={"packet": name, "hash": cur})
    for e in (read_events(root) or []):
        if (e.get("category") == "verify-run" and e.get("packet") == name
                and e.get("hash") == cur):
            return {"recorded": True, "packet": name, "hash": cur}
    return {"recorded": False, "reason": "ledger-unavailable"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Drydock Owner-brief engine")
    ap.add_argument("--write-status", action="store_true")
    ap.add_argument("--lang", default=None, help="status-file language (en, es)")
    ap.add_argument("--record-verify", metavar="NAME", default=None)
    args = ap.parse_args(argv)
    try:
        cwd = Path(os.getcwd()).resolve()
    except OSError:
        cwd = Path(".")
    root = find_drydock_root(cwd, plugin_root_from_env())
    try:
        if args.record_verify:
            print(json.dumps(record_verify(root, args.record_verify), indent=1))
            return 0
        f = facts(root)
        if args.write_status:
            f["status_file"] = write_status(root, f, args.lang)
        print(json.dumps(f, indent=1))
        return 0
    except BaseException:
        # A visible, retryable failure — but still a valid block, never a traceback
        # dressed as facts and never a crash that strands the command.
        print(json.dumps({"drydock": "error", "engine": ENGINE_VERSION,
                          "generated": _today()}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
