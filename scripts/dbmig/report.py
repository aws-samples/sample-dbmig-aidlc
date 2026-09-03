"""Human-readable, phase-aware migration report for a project.

Every phase updates the same file — ``migrations/<project>/migration-report.md`` — so a
person can open it at any time and see **what has been done so far** and **what they
should be aware of / do next**, without reading raw manifests or JSON.

The report is a set of named sections delimited by HTML-comment markers. Each phase
writes/replaces *its own* section idempotently (re-running a phase refreshes its section
rather than appending duplicates); sections are ordered by a stable ``order`` key so the
document always reads Inception → Construction → Validation → Operations.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Dict, List, Tuple

from . import config

_BEGIN = re.compile(
    r"<!--\s*dbmig:section\s+id=(?P<id>[\w.-]+)\s+order=(?P<order>-?\d+)\s*-->"
    r"(?P<body>.*?)<!--\s*/dbmig:section\s*-->",
    re.DOTALL,
)

# The canonical dbmig-aidlc phases. Report sections are keyed and ordered by these so the
# document always reads Inception -> Construction -> Validation -> Operations.
INCEPTION = "inception"
CONSTRUCTION = "construction"
VALIDATION = "validation"
OPERATIONS = "operations"

PHASE_ORDER = {INCEPTION: 10, CONSTRUCTION: 20, VALIDATION: 30, OPERATIONS: 40}
PHASE_TITLE = {
    INCEPTION: "Inception — Assessment & Planning",
    CONSTRUCTION: "Construction — Conversion",
    VALIDATION: "Validation & Testing",
    OPERATIONS: "Operations & Cutover",
}


def update_phase(project: str, phase: str, body_md: str) -> Path:
    """Insert/replace the section for a dbmig-aidlc ``phase`` (see PHASE_ORDER)."""
    if phase not in PHASE_ORDER:
        raise ValueError(f"unknown phase '{phase}' (expected {sorted(PHASE_ORDER)})")
    return update_section(project, phase, PHASE_ORDER[phase], body_md)


def report_path(project: str) -> Path:
    return config.workspace_dir(project) / "migration-report.md"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _parse(text: str) -> Dict[str, Tuple[int, str]]:
    out: Dict[str, Tuple[int, str]] = {}
    for m in _BEGIN.finditer(text or ""):
        out[m.group("id")] = (int(m.group("order")), m.group("body").strip("\n"))
    return out


def _render(project: str, sections: Dict[str, Tuple[int, str]]) -> str:
    head = [
        f"# Migration report — {project}",
        "",
        f"_Last updated: {_now()} · maintained automatically by dbmig._",
        "",
        "This report is refreshed after each phase. It summarizes what has been done, "
        "the current state, and what you should be aware of or do next. It complements "
        "(does not replace) the per-phase artifacts under this workspace.",
        "",
    ]
    ordered: List[Tuple[int, str, str]] = sorted(
        ((order, sid, body) for sid, (order, body) in sections.items()),
        key=lambda t: (t[0], t[1]),
    )
    parts = ["\n".join(head)]
    for order, sid, body in ordered:
        parts.append(
            f"<!-- dbmig:section id={sid} order={order} -->\n{body}\n"
            f"<!-- /dbmig:section -->")
    return "\n\n".join(parts).rstrip() + "\n"


def update_section(project: str, section_id: str, order: int, body_md: str) -> Path:
    """Insert or replace one section of the project migration report.

    ``body_md`` should be the full markdown for the section (typically starting with a
    ``## Heading``). Returns the report path.
    """
    path = report_path(project)
    existing = path.read_text() if path.exists() else ""
    sections = _parse(existing)
    sections[section_id] = (order, body_md.strip("\n"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(project, sections))
    return path
