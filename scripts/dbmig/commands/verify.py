"""``dbmig verify`` — list and record verification of DMS SC VERIFY objects.

VERIFY objects (kept from DMS SC but requiring proof, e.g. `5444` ML/GenAI conversions)
are tracked in a per-schema ledger so a verified object is **not re-verified**. This
command lists the ledger and records verdicts; it also refreshes the Validation section
of the project's ``migration-report.md``.

Examples::

    dbmig verify --schema DEMO --project P                 # list status
    dbmig verify --schema DEMO --project P --set verified \\
        --objects get_customer_full_name,is_in_stock --by donghual --method equivalence-test
    dbmig verify --schema DEMO --project P --set verified --all --note "batch signed off"
"""
from __future__ import annotations

from .. import config, console, report
from ..dmssc import verification as ver


def run(args) -> int:
    schema = args.schema
    ws = config.workspace_dir(args.project)
    lpath = ver.ledger_path(ws, schema)
    if not lpath.exists():
        console.err(f"no verification ledger for schema {schema} in project "
                    f"{args.project} (run `import-dms-sc` first). Expected: {lpath}")
        return 2
    ledger = ver.load_ledger(lpath)
    items = ledger.get("items", {})
    if not items:
        console.warn(f"no VERIFY objects tracked for schema {schema}")
        return 0

    set_to = getattr(args, "set", None)
    if not set_to:
        _list(schema, ledger)
        return 0

    # --- mutate ---
    selectors = None
    if getattr(args, "objects", None):
        selectors = [s for s in args.objects.split(",") if s.strip()]
    if not selectors and not getattr(args, "all", False):
        console.err("specify --objects <names> or --all to choose which objects to mark")
        return 2

    if selectors:
        matched, unmatched = ver.resolve(ledger, selectors)
        if unmatched:
            console.err(f"no VERIFY object matched: {', '.join(unmatched)}")
            if not matched:
                return 2
        target_ids = matched
    else:
        target_ids = list(items.keys())

    try:
        n = ver.set_status(ledger, target_ids, set_to,
                           by=getattr(args, "by", "") or "",
                           note=getattr(args, "note", "") or "",
                           method=getattr(args, "method", "") or "")
    except ValueError as exc:
        console.err(str(exc))
        return 2
    ver.save_ledger(lpath, ledger)

    # keep the migration report's Validation section current
    try:
        report.update_phase(args.project, report.VALIDATION,
                            ver.render_validation_section(ws))
    except Exception:  # noqa: BLE001 - report refresh must not fail the command
        pass

    console.ok(f"marked {n} object(s) as '{set_to}' in schema {schema}")
    _list(schema, ledger)
    return 0


def _list(schema: str, ledger: dict) -> None:
    items = ledger.get("items", {})
    s = ver.summary(ledger)
    console.heading(f"Verification — {schema}")
    print(f"  verified={s[ver.VERIFIED]}  pending={s[ver.PENDING]}  failed={s[ver.FAILED]}"
          f"  (total {sum(s.values())})")
    for sid, e in sorted(items.items(), key=lambda kv: kv[1].get("object", "")):
        badge = {"verified": "✅", "failed": "❌"}.get(e.get("status"), "⏳")
        extra = []
        if e.get("by"):
            extra.append(f"by {e['by']}")
        if e.get("method"):
            extra.append(e["method"])
        if e.get("at"):
            extra.append(e["at"])
        tail = ("  (" + ", ".join(extra) + ")") if extra else ""
        codes = ",".join(e.get("codes", []))
        print(f"  {badge} {e.get('object'):<40} {e.get('status'):<9}"
              f" {('['+codes+']') if codes else ''}{tail}")
