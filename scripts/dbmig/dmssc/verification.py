"""Verification ledger for DMS SC VERIFY-disposition objects.

VERIFY objects (e.g. `5444` ML/GenAI conversions) are kept as-is but must be *proven*
equivalent. Once a human (or an equivalence test) has verified one, that verdict must
persist so the work is not repeated — including across re-imports.

The ledger is therefore a **separate file** that ``import-dms-sc`` merges into (never
blindly overwrites): ``01-assessment/dms-sc-verification-<SCHEMA>.yaml``, keyed by the
stable source node id. The ``dbmig verify`` command lists and updates it.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

PENDING = "pending"
VERIFIED = "verified"
FAILED = "failed"
VALID_STATUSES = {PENDING, VERIFIED, FAILED}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger_path(ws, schema: str) -> Path:
    return Path(ws) / "01-assessment" / f"dms-sc-verification-{schema.upper()}.yaml"


def load_ledger(path: Path) -> dict:
    if Path(path).exists():
        data = yaml.safe_load(Path(path).read_text()) or {}
        if isinstance(data, dict):
            data.setdefault("items", {})
            return data
    return {"items": {}}


def save_ledger(path: Path, ledger: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.safe_dump(ledger, sort_keys=False))


def merge_pending(ledger: dict, project: str, schema: str,
                  verify_objects: Iterable) -> int:
    """Seed a ``pending`` entry for each VERIFY object not already in the ledger.

    Existing entries (any status) are preserved untouched — this is what makes a
    re-import non-destructive to prior verification verdicts. Returns the number of
    new entries added.
    """
    ledger.setdefault("project", project)
    ledger.setdefault("schema", schema.upper())
    items: Dict[str, dict] = ledger.setdefault("items", {})
    added = 0
    for o in verify_objects:
        sid = o.source_id
        if sid in items:
            # keep existing verdict; only refresh the human-readable label
            items[sid]["object"] = f"{o.source_schema}.{o.source_name}"
            continue
        items[sid] = {
            "object": f"{o.source_schema}.{o.source_name}",
            "type": o.source_type,
            "codes": sorted({a.code for a in o.action_items}),
            "status": PENDING,
            "method": "",
            "by": "",
            "at": "",
            "note": "",
        }
        added += 1
    return added


def status_of(ledger: dict, source_id: str) -> str:
    return (ledger.get("items", {}).get(source_id, {}) or {}).get("status", PENDING)


def summary(ledger: dict) -> Dict[str, int]:
    out = {PENDING: 0, VERIFIED: 0, FAILED: 0}
    for entry in ledger.get("items", {}).values():
        s = entry.get("status", PENDING)
        out[s] = out.get(s, 0) + 1
    return out


def resolve(ledger: dict, selectors: List[str]) -> Tuple[List[str], List[str]]:
    """Map user selectors (object name, ``schema.name``, or source id) to ledger keys.

    Returns (matched_source_ids, unmatched_selectors). Matching is case-insensitive
    on the source id, the ``object`` label, and the trailing object name.
    """
    items = ledger.get("items", {})
    matched: List[str] = []
    unmatched: List[str] = []
    for sel in selectors:
        s = sel.strip()
        if not s:
            continue
        low = s.lower()
        hit = None
        for sid, entry in items.items():
            obj = str(entry.get("object", ""))
            name = obj.split(".")[-1]
            if low in (sid.lower(), obj.lower(), name.lower()):
                hit = sid
                break
        if hit:
            matched.append(hit)
        else:
            unmatched.append(sel)
    return matched, unmatched


def set_status(ledger: dict, source_ids: Iterable[str], status: str,
               by: str = "", note: str = "", method: str = "") -> int:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status '{status}' (expected {sorted(VALID_STATUSES)})")
    items = ledger.get("items", {})
    n = 0
    for sid in source_ids:
        entry = items.get(sid)
        if entry is None:
            continue
        entry["status"] = status
        entry["at"] = _now()
        if by:
            entry["by"] = by
        if note:
            entry["note"] = note
        if method:
            entry["method"] = method
        elif status == VERIFIED and not entry.get("method"):
            entry["method"] = "manual"
        n += 1
    return n


def scan_workspace(ws) -> List[Tuple[str, dict]]:
    """Return [(schema, ledger)] for every verification ledger under a workspace."""
    out: List[Tuple[str, dict]] = []
    d = Path(ws) / "01-assessment"
    if not d.is_dir():
        return out
    for f in sorted(d.glob("dms-sc-verification-*.yaml")):
        schema = f.stem[len("dms-sc-verification-"):]
        out.append((schema, load_ledger(f)))
    return out


def render_validation_section(ws) -> str:
    """Human-readable Validation-phase status for VERIFY objects across all schemas."""
    ledgers = scan_workspace(ws)
    lines = [
        f"## {'Validation & Testing'}",
        "",
        "VERIFY objects (kept from DMS SC but requiring proof — e.g. `5444` ML/GenAI "
        "conversions) are tracked here so a verified object is **not re-verified**. "
        "Prove equivalence with `gen-tests` / `run-tests`, then record the verdict with "
        "`dbmig verify --schema <S> --set verified --objects <names>`.",
        "",
    ]
    if not ledgers:
        lines += ["_No VERIFY objects tracked yet._", ""]
        return "\n".join(lines)

    tot = {PENDING: 0, VERIFIED: 0, FAILED: 0}
    lines += ["| Schema | Verified | Pending | Failed | Total |",
              "|---|---|---|---|---|"]
    per_schema_pending: List[Tuple[str, dict]] = []
    for schema, ledger in ledgers:
        s = summary(ledger)
        for k in tot:
            tot[k] += s.get(k, 0)
        total = sum(s.values())
        lines.append(f"| {schema} | {s[VERIFIED]} | {s[PENDING]} | {s[FAILED]} | {total} |")
        per_schema_pending.append((schema, ledger))
    lines.append(f"| **All** | **{tot[VERIFIED]}** | **{tot[PENDING]}** | "
                 f"**{tot[FAILED]}** | **{sum(tot.values())}** |")
    lines.append("")

    # List outstanding (pending/failed) items so people know what still needs attention.
    outstanding = []
    for schema, ledger in per_schema_pending:
        for sid, e in ledger.get("items", {}).items():
            if e.get("status") != VERIFIED:
                outstanding.append((schema, e))
    if outstanding:
        lines += ["**Still to verify:**", ""]
        for schema, e in outstanding:
            codes = ",".join(e.get("codes", []))
            lines.append(f"- `{schema}` · `{e.get('object')}` ({e.get('type')}) "
                         f"— {e.get('status')}"
                         + (f" · codes {codes}" if codes else ""))
        lines.append("")
    else:
        lines += ["All tracked VERIFY objects have been verified. ✅", ""]
    return "\n".join(lines)
