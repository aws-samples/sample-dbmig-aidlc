"""``dbmig decision list|raise|answer|withdraw``.

    ./dbmig decision list   --project P [--open] [--json]
    ./dbmig decision raise  --project P --phase inception --kind fulltext_redesign \
                            --objects DEMO.BOOKS [--question Q --option A="..." ...] [--recommend A]
    ./dbmig decision answer D-001 --choice tsvector --project P [--rationale T]
    ./dbmig decision withdraw D-002 --project P --reason T

Standard kinds (fulltext_redesign, case_insensitive_collation, needs_human,
naming_conflict, fk_guard, diff_conflict, domain_index_redesign) have built-in
questions and options; other kinds need --question and at least two --option.
``answer`` follows the same terminal / chat rule as ``gate approve``.
"""
from __future__ import annotations

import json

from .. import console, decisions as dec
from ..project import ProjectError, load, resolve_dir
from .gate import _channel


def run_list(args) -> int:
    try:
        proj = load(resolve_dir(args))
    except ProjectError as exc:
        console.err(str(exc))
        return 2
    items = dec.list_decisions(proj, phase=args.phase,
                               status="open" if args.open else None)
    if args.json:
        print(json.dumps(items, indent=2))
        return 0
    if not items:
        console.info("no decisions" + (" open" if args.open else ""))
        return 0
    for d in items:
        print(f"{d['id']}  [{d.get('status')}]  {d.get('phase')}/{d.get('kind')}  "
              f"{', '.join(d.get('objects') or [])}")
        print(f"    {d.get('question')}")
        for o in d.get("options") or []:
            mark = "*" if d.get("choice") == o["id"] else ("(recommended)" if o.get("recommended") else "")
            print(f"      {o['id']}: {o['label']} {mark}".rstrip())
        if d.get("status") == "decided":
            print(f"    -> {dec.option_label(d)}  by {d.get('by')} via {d.get('via')} at {d.get('at')}"
                  + (f" — {d['rationale']}" if d.get("rationale") else ""))
    return 0


def _parse_options(raw):
    out = []
    for r in raw or []:
        if "=" not in r:
            raise dec.DecisionError(f"--option needs ID=label, got {r!r}")
        k, v = r.split("=", 1)
        out.append({"id": k.strip(), "label": v.strip()})
    return out


def run_raise(args) -> int:
    try:
        proj = load(resolve_dir(args))
        objs = [o.strip() for o in (args.objects or "").split(",") if o.strip()]
        d, created = dec.raise_decision(
            proj, phase=args.phase, kind=args.kind, objects=objs, question=args.question,
            options=_parse_options(args.option) or None, raised_by=args.raised_by or "cli",
            recommend=args.recommend, detail=args.detail)
    except ProjectError as exc:
        console.err(str(exc))
        return 1
    if not created:
        console.info(f"{d['id']} already exists for {args.kind} {', '.join(objs)} [{d['status']}]")
    elif d["status"] == "decided":
        console.ok(f"{d['id']} answered by questionnaire policy: {dec.option_label(d)}")
    else:
        console.ok(f"raised {d['id']} ({args.kind}) — ask the user, then "
                   f"./dbmig decision answer {d['id']} --choice <id>")
    return 0


def run_answer(args) -> int:
    ch = _channel(args)
    if not ch:
        return 2
    by, via = ch
    try:
        proj = load(resolve_dir(args))
        d = dec.answer(proj, args.id, args.choice, by=by, via=via, rationale=args.rationale)
    except ProjectError as exc:
        console.err(str(exc))
        return 1
    console.ok(f"{d['id']} -> {dec.option_label(d)} (by {by} via {via})")
    return 0


def run_withdraw(args) -> int:
    ch = _channel(args)
    if not ch:
        return 2
    try:
        proj = load(resolve_dir(args))
        d = dec.withdraw(proj, args.id, by=ch[0], reason=args.reason)
    except ProjectError as exc:
        console.err(str(exc))
        return 1
    console.ok(f"{d['id']} withdrawn")
    return 0
