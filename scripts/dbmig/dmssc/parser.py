"""Read a local DMS SC project directory into an :class:`ImportResult`.

Three passes, mirroring the reference ``S3LoaderService``:

1. **Source pass** — every node file under an ``s-<id>/`` directory; skip container
   meta-types; key an object map on the node ``id`` (uppercased) so overloaded routines
   stay distinct; capture the source DDL and coordinates.
2. **Target pass** — every node file under a ``t-<id>/`` directory; the node's
   ``synchronization_object.name`` is the source id — match on it and attach the
   DMS-SC-converted target DDL + target coordinates + inline action items.
3. **Action-item pass** — the ``action-items/<srv>/Schemas.<S>`` statistics files;
   attach structural ``messageActions`` (enriched via the ``*-aid`` catalog) to objects.

Everything is engine- and schema-generic: engines are detected from the ``*-server``
files and object categories from the ``*-ot`` catalog.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .model import ActionItem, DmsScObject, ImportResult

# Container/folder meta-types (plural) that are structural, not real objects. Union of
# the Oracle and SQL Server lists from the reference implementation; leaf object types
# are singular (TABLE, INDEX, FUNCTION, ...) and are always retained.
SKIP_METATYPES = {
    "CLUSTER_KEYS", "CLUSTERS", "COLLECTION_TYPES", "CONNECTION", "CONNECTIONS",
    "CONSTRAINTS", "DATABASE", "DATABASES", "DATABASE_LINKS", "DBMS_JOBS",
    "EXTERNAL_TABLES", "EXTERNAL TABLES", "FUNCTIONS", "GRAPH TABLES", "INDICES",
    "LARGE_OBJECTS", "MAT_VIEWS", "MATERIALIZED_VIEW_LOGS", "MATERIALIZED_VIEWS",
    "NESTED_TABLES", "PARTITIONS", "PACKAGES", "PRIVATE_COLLECTION_TYPES",
    "PRIVATE_CONSTANTS", "PRIVATE_CURSORS", "PRIVATE_EXCEPTIONS", "PRIVATE_FUNCTIONS",
    "PRIVATE_PROCEDURES", "PRIVATE_TYPES", "PRIVATE_VARIABLES", "PROCEDURES", "PROGRAMS",
    "PUBLIC_COLLECTION_TYPES", "PUBLIC_CONSTANTS", "PUBLIC_CURSORS", "PUBLIC_EXCEPTIONS",
    "PUBLIC_FUNCTIONS", "PUBLIC_PROCEDURES", "PUBLIC_TYPES", "PUBLIC_VARIABLES",
    "SCHEDULES", "SCHEMA", "SCHEMAS", "SEQUENCES", "SERVER", "SYNONYMS", "TABLES",
    "TRIGGERS", "TYPES", "USER_DEFINED_TYPES", "USER-DEFINED TYPES", "VIEWS",
    "AGGREGATE FUNCTIONS", "AGGREGATE_FUNCTIONS", "SQL INLINE FUNCTIONS",
    "SQL_INLINE_FUNCTIONS", "SQL SCALAR FUNCTIONS", "SQL_SCALAR_FUNCTIONS",
    "SQL TABLE-VALUED FUNCTIONS", "SQL_TABLE_VALUED_FUNCTIONS", "TABLE TYPES",
    "TABLE_TYPES", "XML SCHEMA COLLECTIONS", "XML_SCHEMA_COLLECTIONS", "ASSEMBLIES",
    "OPERATORS", "DOMAINS", "SCHEDULER", "QUEUING", "SYNONYM_FOLDER",
}

# Inline action-item marker in converted SQL:  [5444 - Severity LOW - <message>]
_INLINE_RE = re.compile(r"\[(\d+)\s*-\s*Severity\s+(\w+)\s*-\s*(.*?)\]", re.DOTALL)
_GENAI_MARK = "generated using GenAI"


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def _content0(doc: Optional[dict]) -> Optional[dict]:
    if not isinstance(doc, dict):
        return None
    arr = doc.get("content")
    if isinstance(arr, list) and arr:
        return arr[0]
    return None


def _node_dirs(root: Path, prefix: str) -> List[Path]:
    return [d for d in root.iterdir()
            if d.is_dir() and d.name.startswith(prefix) and not d.name.endswith("server")]


def _detect_engine(server_file: Path) -> str:
    doc = _read_json(server_file)
    node = _content0(doc)
    if not node:
        return ""
    # server node -> children[0].server_info.vendorName
    children = node.get("children") or []
    if children and isinstance(children[0], dict):
        info = children[0].get("server_info") or {}
        if info.get("vendorName"):
            return str(info["vendorName"])
    info = node.get("server_info") or {}
    return str(info.get("vendorName", ""))


def _load_ot_catalog(action_items_dir: Path) -> Dict[str, str]:
    """meta-type (upper) -> objectTypeProperty (STORAGE_OBJECT/CODE_OBJECT/...)."""
    out: Dict[str, str] = {}
    if not action_items_dir.is_dir():
        return out
    for f in action_items_dir.iterdir():
        if f.is_file() and f.name.endswith("-ot"):
            doc = _read_json(f)
            if isinstance(doc, list):
                for entry in doc:
                    if isinstance(entry, dict):
                        for k, v in entry.items():
                            if isinstance(v, dict) and v.get("objectTypeProperty"):
                                out[k.upper()] = str(v["objectTypeProperty"])
    return out


def _load_aid_catalog(action_items_dir: Path) -> Dict[str, dict]:
    """action-item code -> catalog entry (severityType, topic, actionItem, ...)."""
    out: Dict[str, dict] = {}
    if not action_items_dir.is_dir():
        return out
    for f in action_items_dir.iterdir():
        if f.is_file() and f.name.endswith("-aid"):
            doc = _read_json(f)
            if isinstance(doc, dict):
                for code, entry in doc.items():
                    if isinstance(entry, dict):
                        out[str(code)] = entry
    return out


def _category_for(meta_type: str, ot: Dict[str, str]) -> str:
    prop = ot.get((meta_type or "").upper(), "")
    return {
        "STORAGE_OBJECT": "storage",
        "CODE_OBJECT": "code",
        "SERVER_LEVEL_OBJECT": "server",
    }.get(prop, "other")


def _target_name(locator: dict, meta_type: str, name: str) -> str:
    mt = (meta_type or "").upper()
    specific = {
        "CONSTRAINT": "constraint-name",
        "INDEX": "index-name",
        "DOMAIN": "domain-name",
        "TRIGGER": "trigger-name",
        "FUNCTION": "function-name",
        "PROCEDURE": "procedure-name",
        "VIEW": "view-name",
    }.get(mt)
    if specific and locator.get(specific):
        return str(locator[specific])
    if name:
        return name
    return str(locator.get("table-name", "") or locator.get("name", ""))


def _inline_action_items(sql: str, aid: Dict[str, dict]) -> List[ActionItem]:
    items: List[ActionItem] = []
    for code, sev, msg in _INLINE_RE.findall(sql or ""):
        cat = aid.get(code, {})
        items.append(ActionItem(
            code=code,
            severity=(cat.get("severityType") or sev or "").upper(),
            topic=cat.get("topic", ""),
            message=" ".join((msg or "").split()),
            action=cat.get("actionItem", ""),
            source="inline",
        ))
    return items


def parse_project(dms_sc_dir: str) -> ImportResult:
    root = Path(dms_sc_dir).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"DMS SC project directory not found: {root}")

    result = ImportResult(dms_sc_dir=str(root))
    result.source_engine = _detect_engine(root / "s-server")
    result.target_engine = _detect_engine(root / "t-server")

    ai_dir = root / "action-items"
    ot = _load_ot_catalog(ai_dir)
    aid = _load_aid_catalog(ai_dir)

    obj_by_id: Dict[str, DmsScObject] = {}

    # ---- Pass 1: source nodes -------------------------------------------------
    for sdir in _node_dirs(root, "s-"):
        for f in sdir.iterdir():
            if not f.is_file():
                continue
            node = _content0(_read_json(f))
            if not node:
                continue
            meta = str(node.get("meta-type", "")).upper()
            if not meta or meta in SKIP_METATYPES:
                continue
            sid = str(node.get("id", ""))
            name = str(node.get("name", ""))
            if not sid or not name:
                continue
            locator = node.get("locator") or {}
            obj = DmsScObject(
                source_id=sid,
                source_schema=str(locator.get("schema-name", "")),
                source_name=name,
                source_type=meta,
                source_package=str(locator.get("package-name", "") or ""),
                source_ddl=str(node.get("sql", "") or ""),
                category=_category_for(meta, ot),
            )
            obj_by_id[sid.upper()] = obj

    # ---- Pass 2: target nodes (match by synchronization_object -> source id) --
    for tdir in _node_dirs(root, "t-"):
        for f in tdir.iterdir():
            if not f.is_file():
                continue
            node = _content0(_read_json(f))
            if not node:
                continue
            sync = node.get("synchronization_object")
            src_id = ""
            if isinstance(sync, dict):
                src_id = str(sync.get("name", ""))
            if not src_id:
                continue
            obj = obj_by_id.get(src_id.upper())
            if obj is None:
                continue
            meta = str(node.get("meta-type", "")).upper()
            locator = node.get("locator") or {}
            sql = str(node.get("sql", "") or "")
            obj.target_id = str(node.get("id", ""))
            obj.target_type = meta
            obj.target_ddl = sql
            if locator.get("schema-name"):
                obj.target_schema = str(locator["schema-name"])
            tname = _target_name(locator, meta, str(node.get("name", "")))
            if tname:
                obj.target_name = tname
            if _GENAI_MARK in sql:
                obj.has_genai = True
            # inline action items live in the converted SQL
            for ai in _inline_action_items(sql, aid):
                if not any(x.code == ai.code for x in obj.action_items):
                    obj.action_items.append(ai)

    # ---- Pass 3: structural action items (messageActions) ---------------------
    if ai_dir.is_dir():
        for f in ai_dir.rglob("*"):
            if not f.is_file() or f.name.endswith("-aid") or f.name.endswith("-ot"):
                continue
            doc = _read_json(f)
            if doc is not None:
                _collect_message_actions(doc, obj_by_id, aid, result)

    result.objects = list(obj_by_id.values())
    return result


def _collect_message_actions(node, obj_by_id: Dict[str, DmsScObject],
                             aid: Dict[str, dict], result: ImportResult) -> None:
    """Recurse a treeNodeStatistics document, attaching messageActions to objects."""
    if isinstance(node, dict):
        stat = node.get("statistic")
        if isinstance(stat, dict):
            actions = stat.get("messageActions")
            name = str(node.get("name", ""))
            if isinstance(actions, list) and actions and name:
                obj = obj_by_id.get(name.upper())
                for a in actions:
                    if not isinstance(a, dict):
                        continue
                    code = str(a.get("code") or a.get("messageId") or a.get("id") or "")
                    if not code:
                        continue
                    cat = aid.get(code, {})
                    item = ActionItem(
                        code=code,
                        severity=str(cat.get("severityType", "")).upper(),
                        topic=cat.get("topic", ""),
                        message=cat.get("groupingActionMessage", "") or cat.get("description", ""),
                        action=cat.get("actionItem", ""),
                        source="messageActions",
                    )
                    if obj is not None:
                        if not any(x.code == code for x in obj.action_items):
                            obj.action_items.append(item)
                    else:
                        result.unmatched_action_items.setdefault(name, []).append(item)
        for v in node.values():
            _collect_message_actions(v, obj_by_id, aid, result)
    elif isinstance(node, list):
        for v in node:
            _collect_message_actions(v, obj_by_id, aid, result)


def load_apply_results(dms_sc_dir: str) -> Dict[str, dict]:
    """full-path (upper) -> {status, error} from apply-result/*.csv (best effort)."""
    import csv
    root = Path(dms_sc_dir).expanduser()
    out: Dict[str, dict] = {}
    ar = root / "apply-result"
    if not ar.is_dir():
        return out
    for f in ar.glob("*.csv"):
        try:
            with f.open(newline="", encoding="utf-8", errors="replace") as fh:
                for row in csv.DictReader(fh):
                    fp = (row.get("Full Path") or "").strip()
                    if fp:
                        out[fp.upper()] = {
                            "status": (row.get("Status") or "").strip(),
                            "error": (row.get("Error") or "").strip(),
                        }
        except Exception:
            continue
    return out
