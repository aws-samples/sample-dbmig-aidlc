"""``dbmig gate status|approve|reject`` and ``dbmig project init``.

    ./dbmig gate status  --project P [--json]
    ./dbmig gate approve inception --project P [--note T] [--ack KIND ...|--ack-all]
    ./dbmig gate reject  construction --project P --reason T

On a terminal, approve/reject print the gate summary and ask the user to type the
phase name. From a shell without a TTY (an AI assistant's shell) they are refused
unless ``--approved-by NAME --via chat`` is given; the skills run that only after
the user explicitly approved in the chat.
"""
from __future__ import annotations

import json
import sys

from .. import console, gates
from ..project import GATED_PHASES, ProjectError, load, resolve_dir, whoami

_ICON = {"approved": "✔", "rejected": "✘", "stale": "!", "open": "·"}


def _print_view(v: dict) -> None:
    head = f"{_ICON.get(v['status'], '·')} {v['phase']:<12} {v['status']:<9}"
    if v.get("by"):
        head += f" by {v['by']} at {v['at']}" + (f" via {v['via']}" if v.get("via") else "")
    print(head)
    print(f"    {v['question']}")
    if v.get("note"):
        print(f"    note: {v['note']}")
    if v["status"] != "approved":       # blockers only matter for approving
        for b in v["blockers"]:
            print(f"    blocker: {b}")
    for k, n in v["acknowledgements"].items():
        print(f"    acknowledge: {k} ({n} open)  -> --ack {k}")
    if v["status"] == "stale":
        print("    why stale: what was approved has changed since the approval:")
        for c in v.get("changes") or []:
            print(f"      - {c}")
        print(f"      (usually: {v['likely_cause']})")
        print("    how to fix:")
        for i, s in enumerate(v.get("fix") or [], 1):
            print(f"      {i}. {s}")
    if v.get("waits_on"):
        print(f"    note: still approved, but the earlier gate '{v['waits_on']}' is stale; "
              "re-approve that one first")


def _channel(args):
    """(by, via) or None when refused (no TTY and no explicit chat approval)."""
    via = getattr(args, "via", None)
    by = getattr(args, "approved_by", None)
    if sys.stdin.isatty() and not via:
        return whoami(by), "cli"
    if not (by and via):
        console.err("refused: no terminal to confirm on. An AI assistant may record an "
                    "approval only after the user explicitly approved in the chat, with "
                    "--approved-by <name> --via chat.")
        return None
    return by, via


def _confirm(phase: str) -> bool:
    if not sys.stdin.isatty():
        return True
    try:
        typed = input(f"Type '{phase}' to confirm: ").strip()
    except EOFError:
        return False
    return typed == phase


def run_status(args) -> int:
    try:
        proj = load(resolve_dir(args))
    except ProjectError as exc:
        console.err(str(exc))
        return 2
    views = [gates.view(proj, p) for p in GATED_PHASES]
    if getattr(args, "json", False):
        for v in views:
            v.pop("history", None)
        print(json.dumps({"project": proj.name, "entryPath": proj.entry_path,
                          "schemas": proj.schemas, "next": gates.next_gate(proj),
                          "gates": views}, indent=2))
        return 0
    console.heading(f"Gates — {proj.name} ({proj.data.get('pair')}, entry {proj.entry_path}, "
                    f"schemas {', '.join(proj.schemas) or '-'})")
    for v in views:
        _print_view(v)
    nxt = gates.next_gate(proj)
    print(f"next gate: {nxt}" if nxt else "all gates approved")
    return 0


def run_approve(args) -> int:
    ch = _channel(args)
    if not ch:
        return 2
    by, via = ch
    try:
        proj = load(resolve_dir(args))
        if via == "cli":
            _print_view(gates.view(proj, args.phase))
            if not _confirm(args.phase):
                console.err("not confirmed; nothing recorded")
                return 1
        v = gates.approve(proj, args.phase, by=by, via=via, note=args.note,
                          ack=args.ack or [], ack_all=args.ack_all)
    except ProjectError as exc:
        console.err(str(exc))
        return 1
    console.ok(f"gate '{args.phase}' approved by {v['by']} via {v['via']} at {v['at']}")
    return 0


def run_reject(args) -> int:
    ch = _channel(args)
    if not ch:
        return 2
    by, via = ch
    try:
        proj = load(resolve_dir(args))
        if via == "cli" and not _confirm(args.phase):
            console.err("not confirmed; nothing recorded")
            return 1
        v = gates.reject(proj, args.phase, by=by, via=via, reason=args.reason)
    except ProjectError as exc:
        console.err(str(exc))
        return 1
    console.ok(f"gate '{args.phase}' rejected by {v['by']} via {v['via']}: {v['note']}")
    return 0


def run_project_init(args) -> int:
    ws = resolve_dir(args)
    from ..project import exists
    if exists(ws):
        console.info(f"{ws / 'project.yaml'} already exists")
        return 0
    proj = load(ws, name=getattr(args, "project", None) or ws.name)
    console.ok(f"created {proj.file} (entry {proj.entry_path}, pair {proj.data.get('pair')}, "
               f"schemas {', '.join(proj.schemas) or '-'})")
    return 0
