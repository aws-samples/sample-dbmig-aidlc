"""Questionnaire intake (optional mode): markdown files the customer answers.

Round 1 (``00-intake/questionnaire.md``) is generated from
``engines/_common/questionnaire.yaml`` plus ``engines/<pair>/questionnaire.yaml`` and
collects project, connection (no passwords), scope, strategy and policy answers.
Round 2 (``01-assessment/decisions-questionnaire.md``) lists the open decisions that
no round-1 policy answered.

This module only parses and writes; it never interprets free text. "Other" answers
are reported back so the AI assistant can clarify them with the user.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from . import config
from .project import load_yaml

ROUND1 = "00-intake/questionnaire.md"
ROUND2 = "01-assessment/decisions-questionnaire.md"
ROOT_FILE = "questionnaire.md"
MARK = "<!-- dbmig questionnaire"
_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVW"


class QuestionnaireError(Exception):
    pass


# ---- question sources ---------------------------------------------------------

def _yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data if isinstance(data, dict) else {}


def load_sections(pair: Optional[str], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = root or config.find_repo_root()
    secs = list(_yaml(root / "engines" / "_common" / "questionnaire.yaml").get("sections") or [])
    if pair:
        secs += list(_yaml(root / "engines" / pair / "questionnaire.yaml").get("sections") or [])
    return secs


def _questions(sections) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    return [(s, q) for s in sections for q in (s.get("questions") or [])]


def _qtype(q: Dict[str, Any]) -> str:
    return q.get("type") or ("choice" if q.get("options") else "text")


# ---- conditions ---------------------------------------------------------------

def _cond(expr: Optional[str], vals: Dict[str, Any]) -> bool:
    """``key == v`` / ``key != v`` / ``key in [a, b]`` joined by `` and ``."""
    if not expr:
        return True
    for part in str(expr).split(" and "):
        m = re.match(r"^\s*(\w+)\s*(==|!=|in)\s*(.+?)\s*$", part)
        if not m:
            raise QuestionnaireError(f"bad applies_when: {expr!r}")
        key, op, rhs = m.groups()
        cur = str(vals.get(key, "") if vals.get(key) is not None else "").lower()
        if op == "in":
            opts = [x.strip().strip("'\"").lower() for x in rhs.strip("[]").split(",")]
            ok = cur in opts
        else:
            ok = (cur == rhs.strip("'\"").lower()) == (op == "==")
        if not ok:
            return False
    return True


# ---- markdown parse -------------------------------------------------------------

_QHEAD = re.compile(r"^###\s+(Q[\d.]+|D-\d+)\b")
_SHEAD = re.compile(r"^##\s+(?:Section\s+)?([\w.]+)\b")
_ANS = re.compile(r"^\s*\[Answer\]:\s?(.*)$")
_BY = re.compile(r"^\s*\[Answered by\]:\s?(.*)$")


def parse(text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return ({question id: raw answer}, {section id: answered by})."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    answers: Dict[str, str] = {}
    by: Dict[str, str] = {}
    cur_q, cur_s, buf, collecting = None, None, [], False

    def flush():
        if cur_q is not None and collecting:
            answers[cur_q] = "\n".join(buf).strip()

    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            flush()
            cur_q, buf, collecting = None, [], False
            m = _SHEAD.match(line)
            cur_s = m.group(1) if m else None
            continue
        m = _QHEAD.match(line)
        if m:
            flush()
            cur_q, buf, collecting = m.group(1), [], False
            continue
        if line.strip() == "---":
            flush()
            cur_q, buf, collecting = None, [], False
            continue
        m = _BY.match(line)
        if m and cur_q is None and cur_s:
            by[cur_s] = m.group(1).strip()
            continue
        m = _ANS.match(line)
        if m and cur_q is not None:
            collecting, buf = True, [m.group(1)]
            continue
        if collecting:
            buf.append(line)
    flush()
    return answers, by


# ---- answer interpretation -------------------------------------------------------

def _default_for(q, vals):
    for key, mapping in (q.get("default_by") or {}).items():
        v = str(vals.get(key, "")).lower()
        if v in {str(k).lower() for k in mapping}:
            return {str(k).lower(): x for k, x in mapping.items()}[v]
    return q.get("default")


def interpret(q: Dict[str, Any], raw: str, vals: Dict[str, Any]) -> Dict[str, Any]:
    """{'status': ok|missing|invalid|other, 'value', 'option', 'other', 'error'}"""
    t = _qtype(q)
    raw = (raw or "").strip()
    if not raw:
        if q.get("optional"):
            if t == "choice":
                rec = next((o for o in q["options"] if o.get("recommended")), None)
                if rec:
                    return {"status": "ok", "option": rec["id"],
                            "value": rec.get("value", rec["id"]), "defaulted": True}
                return {"status": "ok", "value": None, "defaulted": True}
            return {"status": "ok", "value": _default_for(q, vals), "defaulted": True}
        return {"status": "missing"}
    if t == "choice":
        m = re.match(r"^\s*([A-Za-z])\s*(?:[).:\-]\s*|\s+|$)(.*)$", raw, flags=re.S)
        letter = m.group(1).upper() if m else None
        if letter == "X" or raw.lower().startswith("other"):
            rest = (m.group(2) if letter == "X" else raw[5:]).strip(" :-\n")
            if not rest:
                return {"status": "invalid", "error": "Other (X) needs a description"}
            return {"status": "other", "option": "X", "other": rest, "value": None}
        for o in q["options"]:
            if letter == str(o["id"]).upper() or raw.lower() == str(o.get("value", "")).lower():
                return {"status": "ok", "option": o["id"], "value": o.get("value", o["id"])}
        return {"status": "invalid",
                "error": f"answer with one of {', '.join(o['id'] for o in q['options'])} or X) Other"}
    if t == "int":
        try:
            return {"status": "ok", "value": int(raw)}
        except ValueError:
            return {"status": "invalid", "error": "expected a number"}
    if t == "list":
        return {"status": "ok", "value": [x.strip() for x in re.split(r"[,\n]", raw) if x.strip()]}
    if q.get("validate") == "env_var" and not _ENV_RE.match(raw):
        return {"status": "invalid",
                "error": "give the NAME of an environment variable (letters, digits, _), never a password"}
    return {"status": "ok", "value": raw}


def evaluate(sections, answers: Dict[str, str]) -> Dict[str, Any]:
    """Interpret every applicable question in order. Returns
    {'results': {qid: result}, 'values': {key: value}, 'applicable': [qid], 'missing',
     'invalid', 'other'}."""
    vals: Dict[str, Any] = {}
    results: Dict[str, Dict[str, Any]] = {}
    applicable: List[str] = []
    for _, q in _questions(sections):
        if not _cond(q.get("applies_when"), vals):
            continue
        applicable.append(q["id"])
        r = interpret(q, answers.get(q["id"], ""), vals)
        results[q["id"]] = r
        if r["status"] == "ok":
            vals[q["key"]] = r.get("value")
    return {
        "results": results, "values": vals, "applicable": applicable,
        "missing": [i for i in applicable if results[i]["status"] == "missing"],
        "invalid": [(i, results[i]["error"]) for i in applicable if results[i]["status"] == "invalid"],
        "other": [(i, results[i]["other"]) for i in applicable if results[i]["status"] == "other"],
    }


def pair_from(values: Dict[str, Any]) -> Optional[str]:
    s, t = values.get("source_engine"), values.get("target_engine")
    return f"{s}-to-{t}" if s and t else None


# ---- render -------------------------------------------------------------------

_INTRO = """\
# Migration questionnaire — round 1

Answer each question on its `[Answer]:` line: the option letter (for example `A`), or
`X) <your own answer>` for something else. Blank answers on questions marked *(optional)*
take the recommended option. Several people can fill in different sections; put your name
on the section's `[Answered by]:` line.

**Never write a password in this file.** Give the name of the environment variable or the
AWS Secrets Manager secret that holds it.

When you are done, tell the assistant ("the questionnaire is answered"), or run
`./dbmig questionnaire check`. Questions that are still missing or unclear are listed
back to you; nothing is applied until you confirm.
"""


def _render_q(q: Dict[str, Any], ans: str) -> List[str]:
    opt = " *(optional)*" if q.get("optional") else ""
    out = [f"### {q['id']} {q['text']}{opt}", ""]
    if q.get("help"):
        out += [f"_{q['help']}_", ""]
    if q.get("options"):
        for o in q["options"]:
            rec = " **(recommended)**" if o.get("recommended") else ""
            out.append(f"- {o['id']}) {o['label']}{rec}")
        out += ["- X) Other (describe)", ""]
    out += [f"[Answer]: {ans}".rstrip(), ""]
    return out


def render_round1(sections, answers: Dict[str, str], by: Dict[str, str],
                  *, pair: Optional[str]) -> str:
    vals = evaluate(sections, answers)["values"]
    lines = [f"{MARK} round=1 pair={pair or 'unknown'} -->", _INTRO]
    if not pair:
        lines += ["> The conversion-policy questions for your engine pair are added after you "
                  "answer Q2.1 and Q2.3 and run `./dbmig questionnaire check`. Your answers "
                  "are kept.", ""]
    for s in sections:
        qs = [q for q in s.get("questions") or [] if _cond(q.get("applies_when"), vals)
              or answers.get(q["id"])]
        if not qs:
            continue
        lines += ["---", "", f"## Section {s['id']} — {s['title']}", ""]
        if s.get("note"):
            lines += [str(s["note"]).strip(), ""]
        lines += [f"[Answered by]: {by.get(str(s['id']), '')}".rstrip(), ""]
        for q in qs:
            cond = q.get("applies_when")
            if cond:
                lines += [f"<!-- only when {cond} -->"]
            lines += _render_q(q, answers.get(q["id"], ""))
    return "\n".join(lines).rstrip() + "\n"


def render_round2(project_name: str, open_decisions: List[Dict[str, Any]],
                  answers: Dict[str, str]) -> str:
    lines = [f"{MARK} round=2 -->",
             f"# Migration questionnaire — round 2 ({project_name})", "",
             "The assessment found these decisions that your round-1 answers did not cover. "
             "Answer each on its `[Answer]:` line with the option letter, or `X) <your own "
             "answer>`. Then tell the assistant, or run `./dbmig questionnaire check --round 2`.",
             "", "## Section D — Decisions", "",
             f"[Answered by]: {answers.get('_by', '')}".rstrip(), ""]
    for d in open_decisions:
        lines += ["---", "", f"### {d['id']} {d['question']}", "",
                  f"Kind: `{d['kind']}` · Objects: {', '.join(d.get('objects') or []) or '-'}", ""]
        if d.get("detail"):
            lines += [f"_{d['detail']}_", ""]
        for letter, o in zip(_LETTERS, d.get("options") or []):
            rec = " **(recommended)**" if o.get("recommended") else ""
            lines.append(f"- {letter}) {o['label']}{rec}")
        lines += ["- X) Other (describe)", "", f"[Answer]: {answers.get(d['id'], '')}".rstrip(), ""]
    return "\n".join(lines).rstrip() + "\n"


def round2_choice(d: Dict[str, Any], raw: str) -> Dict[str, Any]:
    """Map a round-2 letter answer onto the decision's option id."""
    opts = [{"id": letter, "value": o["id"], "label": o["label"]}
            for letter, o in zip(_LETTERS, d.get("options") or [])]
    return interpret({"id": d["id"], "options": opts}, raw, {})


# ---- prefill from existing files ---------------------------------------------------

def _dig(d: Dict[str, Any], dotted: str):
    for part in dotted.split("."):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d


def prefill(sections, conn: Dict[str, Any], mig: Dict[str, Any]) -> Dict[str, str]:
    """Answers taken from an existing connections.yaml / migration-config.yaml."""
    out: Dict[str, str] = {}
    for _, q in _questions(sections):
        for w in q.get("writes_to") or []:
            if w.startswith("config:"):
                v = _dig(mig, w[7:])
            elif w.startswith("connections:"):
                v = _dig(conn, w[12:])
            else:
                continue
            if v is None or v == "" or v == []:
                continue
            if w.endswith(".password"):
                m = re.fullmatch(r"\$\{(\w+)\}", str(v))
                if not m:
                    continue          # never copy a literal password
                v = m.group(1)
            if w.endswith(".engine"):
                v = config.normalize_engine(str(v))
            if q.get("options"):
                hit = next((o["id"] for o in q["options"] if str(o.get("value", "")).lower()
                            == str(v).lower()), None)
                if hit:
                    out[q["id"]] = hit
            elif isinstance(v, list):
                out[q["id"]] = ", ".join(str(x) for x in v)
            else:
                out[q["id"]] = str(v)
    return out


# ---- writers ----------------------------------------------------------------------

def _set(d: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def build_outputs(sections, ev: Dict[str, Any], *, source: str, by: Dict[str, str],
                  default_by: str, when: str) -> Dict[str, Any]:
    """From evaluated answers: {'config': {...}, 'connections': {...}, 'intake': {...},
    'policies': {...}} (only answered/defaulted values; Other answers excluded)."""
    cfg: Dict[str, Any] = {}
    conn: Dict[str, Any] = {}
    intake: Dict[str, Any] = {}
    policies: Dict[str, Any] = {}
    for s, q in _questions(sections):
        r = ev["results"].get(q["id"])
        if not r:
            continue
        who = by.get(str(s["id"])) or default_by
        for w in q.get("writes_to") or []:
            if w == "policy":
                if r["status"] == "other":
                    policies[q["key"]] = {"choice": "X", "other": r["other"], "guidance": r["other"],
                                          "source": f"{source}#{q['id']}", "by": who, "at": when,
                                          "via": "questionnaire", "needs_review": True}
                elif r["status"] == "ok" and r.get("option"):
                    o = next(x for x in q["options"] if x["id"] == r["option"])
                    pol = {"choice": o["id"], "label": o["label"], "source": f"{source}#{q['id']}",
                           "by": who, "at": when, "via": "questionnaire"}
                    if o.get("guidance"):
                        pol["guidance"] = o["guidance"]
                    if o.get("resolves"):
                        pol["resolves"] = dict(o["resolves"])
                    if r.get("defaulted"):
                        pol["defaulted"] = True
                    policies[q["key"]] = pol
                continue
            if r["status"] != "ok" or r.get("value") is None:
                continue
            v = r["value"]
            if w == "intake":
                intake[q["key"]] = v
            elif w.startswith("config:"):
                _set(cfg, w[7:], v)
            elif w.startswith("connections:"):
                path = w[12:]
                if path.endswith(".password"):
                    v = "${%s}" % v
                if path == "source.service_name" and str(v).lower().startswith("sid:"):
                    path, v = "source.sid", str(v)[4:].strip()
                _set(conn, path, v)
    if "schemas" in (cfg.get("scope") or {}):
        cfg["scope"]["schemas"] = [str(x).upper() for x in cfg["scope"]["schemas"]]
    return {"config": cfg, "connections": conn, "intake": intake, "policies": policies}


def merge(base: Dict[str, Any], upd: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def changed_keys(old: Dict[str, Any], new: Dict[str, Any], prefix: str = "") -> List[str]:
    out = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        p = f"{prefix}{k}"
        if isinstance(a, dict) and isinstance(b, dict):
            out += changed_keys(a, b, p + ".")
        elif a != b and k in old:
            out.append(f"{p}: {a!r} -> {b!r}")
    return out


def policies_block(ws: Path) -> str:
    """Policies + answered decisions from project.yaml, as markdown for the
    conversion/test context (customer-specific precedence)."""
    f = ws / "project.yaml"
    if not f.exists():
        return ""
    data = load_yaml(f) or {}
    lines = []
    for key, p in (data.get("policies") or {}).items():
        if isinstance(p, dict) and p.get("guidance"):
            flag = " (free-text answer; confirm with the user if unclear)" if p.get("needs_review") else ""
            lines.append(f"- **{key}**: {p['guidance']}{flag}")
    decided = []
    for d in data.get("decisions") or []:
        if d.get("status") == "decided":
            label = next((o.get("label") for o in d.get("options") or []
                          if o.get("id") == d.get("choice")), d.get("choice"))
            decided.append(f"- {d.get('id')} ({d.get('kind')}, {', '.join(d.get('objects') or [])}): "
                           f"**{label}**" + (f" — {d['rationale']}" if d.get("rationale") else ""))
    if not lines and not decided:
        return ""
    out = ["# CUSTOMER DECISIONS — HIGHEST PRECEDENCE",
           "Recorded in project.yaml (questionnaire policies and answered decisions). Apply "
           "them; they override the general playbook guidance below. Cite the policy key or "
           "decision id in the conversion log where you apply one.", ""]
    if lines:
        out += ["## Policies", ""] + lines + [""]
    if decided:
        out += ["## Answered decisions", ""] + decided
    return "\n".join(out).rstrip()
