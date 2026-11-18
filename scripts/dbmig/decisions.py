"""Decision queue in ``project.yaml``.

A decision records an ambiguity that needs a human choice (principle 4: ask, never
assume) so it survives the chat session and is visible on the review site.

- ``raise_decision`` de-duplicates on (kind, objects). When a questionnaire policy
  maps this kind to one of the decision's options, the decision is answered at once
  with ``via: questionnaire``; otherwise it stays open and the agent asks.
- ``answer`` is a user action (CLI, or chat where the agent runs the CLI after the
  user chose). ``needs_human`` answers also update the unit in its manifest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from .project import PHASES, VIA, Project, ProjectError, load_yaml, now


class DecisionError(ProjectError):
    pass


# Standard options per decision kind. Stable ids let questionnaire policies map an
# answer onto a later decision (questionnaire option -> {kind: option id}).
KIND_OPTIONS: Dict[str, Dict[str, Any]] = {
    "fulltext_redesign": {
        "question": "How should the Oracle Text (CONTEXT/CTXCAT) index be redesigned on the target?",
        "options": [
            {"id": "native", "label": "Native full-text search: generated tsvector column + GIN index",
             "recommended": True},
            {"id": "trigram", "label": "Substring search with pg_trgm GIN index"},
            {"id": "external", "label": "Move search to an external engine (e.g. Amazon OpenSearch Service); "
                                        "drop the index from the migration"},
            {"id": "drop", "label": "Drop the index; the application no longer needs it"},
        ],
    },
    "fulltext_redesign@mysql": {
        "question": "How should the Oracle Text (CONTEXT/CTXCAT) index be redesigned on MySQL?",
        "options": [
            {"id": "native", "label": "MySQL FULLTEXT index (InnoDB) with MATCH ... AGAINST",
             "recommended": True},
            {"id": "external", "label": "Move search to an external engine (e.g. Amazon OpenSearch Service); "
                                        "drop the index from the migration"},
            {"id": "drop", "label": "Drop the index; the application no longer needs it"},
        ],
    },
    "domain_index_redesign": {
        "question": "The domain index has no 1:1 target equivalent. How should it be handled?",
        "options": [
            {"id": "redesign", "label": "Redesign with a native target index type", "recommended": True},
            {"id": "drop", "label": "Drop the index from the migration"},
        ],
    },
    "case_insensitive_collation": {
        "question": "Case-insensitive collation on the source: how should string comparisons behave on the target?",
        "options": [
            {"id": "citext", "label": "citext for the compared/searched columns", "recommended": True},
            {"id": "icu", "label": "ICU nondeterministic collation (no LIKE before PostgreSQL 18)"},
            {"id": "app", "label": "Keep case-sensitive; the application uses ILIKE / lower()"},
        ],
    },
    "case_insensitive_collation@mysql": {
        "question": "Case-insensitive collation on the source: which MySQL collation should the target use?",
        "options": [
            {"id": "ci", "label": "Case-insensitive utf8mb4_0900_ai_ci (keeps the source behaviour)",
             "recommended": True},
            {"id": "cs", "label": "Case-sensitive utf8mb4_0900_as_cs; the application adapts"},
        ],
    },
    "naming_conflict@mysql": {
        "question": "Several source routines flatten to the same '<package>_<subprogram>' "
                    "MySQL name. How should they be disambiguated?",
        "options": [
            {"id": "separator", "label": "Use a distinct separator, e.g. pkg$routine", "recommended": True},
            {"id": "rename", "label": "Rename the colliding converted routine(s) individually"},
        ],
    },
    "needs_human": {
        "question": "The unit failed to apply after the maximum retries. What next?",
        "options": [
            {"id": "fix", "label": "I fix the converted file by hand; re-apply it", "recommended": True},
            {"id": "rule", "label": "Re-convert with my guidance (rationale is passed to the converter)"},
            {"id": "skip", "label": "Leave it out of the migration (documented)"},
        ],
    },
    "naming_conflict": {
        "question": "Several source routines flatten to the same '<package>_<subprogram>' "
                    "target name. How should they be disambiguated?",
        "options": [
            {"id": "schema_per_package", "label": "One target schema per package (pkg.routine keeps its name)",
             "recommended": True},
            {"id": "separator", "label": "Use a distinct separator, e.g. pkg$routine"},
            {"id": "rename", "label": "Rename the colliding converted routine(s) individually"},
        ],
    },
    "fk_guard": {
        "question": "The converted unit has more foreign keys than the source. What next?",
        "options": [
            {"id": "rule", "label": "Re-convert without the extra foreign key(s)", "recommended": True},
            {"id": "fix", "label": "I fix the converted file by hand; re-apply it"},
            {"id": "accept", "label": "Keep the extra foreign key(s) (intended)"},
        ],
    },
    "diff_conflict": {
        "question": "DMS SC converted this object, but it is MISSING on the live target. What next?",
        "options": [
            {"id": "apply-ours", "label": "Apply the DMS SC DDL to the target", "recommended": True},
            {"id": "keep-live", "label": "Leave it missing on the target (documented)"},
            {"id": "reconvert", "label": "Reconvert it (MANUAL) before applying"},
        ],
    },
}


def auto_raise(project: str, *, phase: str, kind: str, objects: List[str],
               raised_by: str, detail: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Raise a standard decision from a command; never fails the command."""
    from . import config, console
    from .project import load
    try:
        proj = load(config.workspace_dir(project))
        d, created = raise_decision(proj, phase=phase, kind=kind, objects=objects,
                                    raised_by=raised_by, detail=detail)
    except Exception as exc:  # noqa: BLE001 - decisions are bookkeeping here
        console.warn(f"could not record decision ({kind} {', '.join(objects)}): {exc}")
        return None
    if created:
        tail = (f"answered by questionnaire policy: {option_label(d)}"
                if d["status"] == "decided" else "open — ask the user")
        console.info(f"decision {d['id']} [{kind}] {', '.join(objects)}: {tail}")
    return d


def _key(kind: str, objects: Iterable[str]) -> str:
    return f"{kind}|{','.join(sorted(str(o).upper() for o in objects))}"


def standard(kind: str, pair: Optional[str] = None) -> Dict[str, Any]:
    """Built-in question/options for ``kind``; target-specific variants
    (``kind@mysql``) win for that target."""
    target = (pair or "").split("-to-")[-1] if pair else ""
    return KIND_OPTIONS.get(f"{kind}@{target}") or KIND_OPTIONS.get(kind) or {}


def _next_id(proj: Project) -> str:
    n = 0
    for d in proj.decisions:
        try:
            n = max(n, int(str(d.get("id", "D-0")).split("-")[-1]))
        except ValueError:
            pass
    return f"D-{n + 1:03d}"


def list_decisions(proj: Project, *, phase: Optional[str] = None,
                   status: Optional[str] = None) -> List[Dict[str, Any]]:
    return [d for d in proj.decisions
            if (not phase or d.get("phase") == phase)
            and (not status or d.get("status", "open") == status)]


def open_decisions(proj: Project, phase: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_decisions(proj, phase=phase, status="open")


def find(proj: Project, did: str) -> Dict[str, Any]:
    for d in proj.decisions:
        if str(d.get("id")).upper() == did.upper():
            return d
    raise DecisionError(f"decision {did} not found")


def _policy_choice(proj: Project, kind: str, options: List[Dict[str, Any]]
                   ) -> Optional[Tuple[str, Dict[str, Any], str]]:
    """(option id, policy record, policy key) when a policy answers this kind."""
    ids = {o["id"] for o in options}
    for key, pol in (proj.data.get("policies") or {}).items():
        if not isinstance(pol, dict):
            continue
        target = (pol.get("resolves") or {}).get(kind)
        if target and target in ids:
            return target, pol, key
    return None


def raise_decision(proj: Project, *, phase: str, kind: str, objects: List[str],
                   question: Optional[str] = None,
                   options: Optional[List[Dict[str, Any]]] = None,
                   raised_by: str = "cli", recommend: Optional[str] = None,
                   detail: Optional[str] = None, save: bool = True
                   ) -> Tuple[Dict[str, Any], bool]:
    """Raise (or return the existing) decision. Returns ``(decision, created)``."""
    if phase not in PHASES:
        raise DecisionError(f"unknown phase {phase}")
    std = standard(kind, proj.data.get("pair"))
    question = question or std.get("question")
    options = [dict(o) for o in (options or std.get("options") or [])]
    if not question:
        raise DecisionError(f"decision kind {kind} needs --question")
    if len(options) < 2:
        raise DecisionError("a decision needs at least two options")
    if recommend:
        if recommend not in {o["id"] for o in options}:
            raise DecisionError(f"--recommend {recommend} is not an option id")
        for o in options:
            o["recommended"] = o["id"] == recommend
    key = _key(kind, objects)
    for d in proj.decisions:
        if d.get("status") != "withdrawn" and _key(d.get("kind", ""), d.get("objects") or []) == key:
            return d, False
    d: Dict[str, Any] = {
        "id": _next_id(proj), "phase": phase, "kind": kind, "objects": list(objects),
        "question": question, "options": options, "raisedBy": raised_by,
        "raisedAt": now(), "status": "open",
    }
    if detail:
        d["detail"] = detail
    pc = _policy_choice(proj, kind, options)
    if pc:
        choice, pol, pkey = pc
        d.update({"status": "decided", "choice": choice, "by": pol.get("by") or "questionnaire",
                  "at": now(), "via": "questionnaire",
                  "rationale": f"answered in advance by policy '{pkey}'"
                               + (f" ({pol['source']})" if pol.get("source") else ""),
                  "policy": pkey})
    proj.decisions.append(d)
    if save:
        proj.save()
    return d, True


def resolve_by_policies(proj: Project) -> List[Dict[str, Any]]:
    """Answer open decisions that a (newly recorded) policy covers."""
    done = []
    for d in open_decisions(proj):
        pc = _policy_choice(proj, d.get("kind", ""), d.get("options") or [])
        if not pc:
            continue
        choice, pol, pkey = pc
        d.update({"status": "decided", "choice": choice, "by": pol.get("by") or "questionnaire",
                  "at": now(), "via": "questionnaire", "policy": pkey,
                  "rationale": f"answered in advance by policy '{pkey}'"
                               + (f" ({pol['source']})" if pol.get("source") else "")})
        done.append(d)
    if done:
        proj.save()
    return done


def answer(proj: Project, did: str, choice: str, *, by: str, via: str = "cli",
           rationale: Optional[str] = None) -> Dict[str, Any]:
    if via not in VIA:
        raise DecisionError(f"--via must be one of {', '.join(VIA)}")
    d = find(proj, did)
    ids = [o["id"] for o in d.get("options") or []]
    if choice not in ids:
        raise DecisionError(f"option {choice} is not one of {', '.join(ids)}")
    if d.get("status") == "withdrawn":
        raise DecisionError(f"decision {did} was withdrawn")
    d.update({"status": "decided", "choice": choice, "by": by, "at": now(), "via": via})
    if rationale:
        d["rationale"] = rationale
    else:
        d.pop("rationale", None)
    d.pop("policy", None)
    proj.save()
    apply_effects(proj, d)
    return d


def withdraw(proj: Project, did: str, *, by: str, reason: str) -> Dict[str, Any]:
    d = find(proj, did)
    if d.get("status") != "open":
        raise DecisionError(f"decision {did} is {d.get('status')}, not open")
    d.update({"status": "withdrawn", "by": by, "at": now(), "rationale": reason})
    proj.save()
    return d


def option_label(d: Dict[str, Any]) -> str:
    for o in d.get("options") or []:
        if o.get("id") == d.get("choice"):
            return str(o.get("label"))
    return str(d.get("choice") or d.get("status"))


def decided_text(proj: Project, objects: Optional[Iterable[str]] = None) -> str:
    """Answered decisions as markdown lines, for conversion prompts."""
    want = {o.upper() for o in objects} if objects is not None else None
    lines = []
    for d in list_decisions(proj, status="decided"):
        objs = [str(o) for o in d.get("objects") or []]
        if want is not None and not any(o.upper() in want for o in objs):
            continue
        lines.append(f"- {d['id']} ({d['kind']}, {', '.join(objs)}): {d['question']} -> "
                     f"**{option_label(d)}**" + (f" — {d['rationale']}" if d.get("rationale") else ""))
    return "\n".join(lines)


# ---- needs_human effects on manifests -------------------------------------

def _manifest_paths(proj: Project, schema: str) -> List[Path]:
    c = proj.path("02-construction")
    return [c / f"manifest-{schema.upper()}.yaml", c / f"code-manifest-{schema.upper()}.yaml"]


def apply_effects(proj: Project, d: Dict[str, Any]) -> None:
    """``needs_human`` answers move the unit on: fix -> converted (re-apply the
    hand-edited file), rule -> pending (re-convert), skip -> skipped."""
    if d.get("status") != "decided" or d.get("kind") != "needs_human":
        return
    for obj in d.get("objects") or []:
        if "." not in obj:
            continue
        schema, name = obj.split(".", 1)
        for f in _manifest_paths(proj, schema):
            if not f.exists():
                continue
            m = load_yaml(f) or {}
            changed = False
            for u in m.get("units") or []:
                if str(u.get("name", "")).upper() != name.upper():
                    continue
                post = u.get("status") == "applied" and u.get("post_status") == "needs_human"
                field = "post_status" if post else "status"
                if d["choice"] == "fix":
                    u[field] = "pending" if post else "converted"
                elif d["choice"] == "rule":
                    u["status"] = "pending"
                    if post:
                        u["post_status"] = "pending"
                elif d["choice"] == "skip":
                    u[field] = "skipped"
                u["attempts"] = 0
                changed = True
            if changed:
                f.write_text(yaml.safe_dump(m, sort_keys=False))
