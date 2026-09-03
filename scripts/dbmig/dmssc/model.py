"""Data model for a parsed DMS SC project."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ActionItem:
    """A single DMS SC action item attached to an object.

    ``code`` is the DMS SC issue code (e.g. ``5444``). ``severity``/``topic``/``action``
    are enriched from the ``*-aid`` catalog when available. ``source`` records where we
    found it: ``inline`` (a ``/* [code - Severity X - msg] */`` comment in the converted
    SQL) or ``messageActions`` (the structural per-schema statistics file).
    """
    code: str
    severity: str = ""
    topic: str = ""
    message: str = ""
    action: str = ""
    source: str = "inline"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "topic": self.topic,
            "message": self.message,
            "action": self.action,
            "source": self.source,
        }


@dataclass
class DmsScObject:
    """One source object and its DMS-SC-converted target counterpart."""
    source_id: str
    source_schema: str = ""
    source_name: str = ""
    source_type: str = ""          # leaf meta-type, e.g. TABLE / FUNCTION / INDEX
    source_package: str = ""
    source_ddl: str = ""

    target_id: str = ""
    target_schema: str = ""
    target_name: str = ""
    target_type: str = ""
    target_ddl: str = ""

    category: str = "other"        # storage | code | server | other (from *-ot catalog)
    has_genai: bool = False
    action_items: List[ActionItem] = field(default_factory=list)
    apply_status: str = ""         # SUCCESS | ERROR | "" (from apply-result CSV)
    apply_error: str = ""
    disposition: str = ""          # accept | verify | manual (set by classify)

    # snapshot file references (filled by the command when it writes DDL to disk)
    source_ddl_ref: str = ""
    target_ddl_ref: str = ""

    @property
    def has_target(self) -> bool:
        return bool(self.target_ddl or self.target_id)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_schema": self.source_schema,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "source_package": self.source_package,
            "target_id": self.target_id,
            "target_schema": self.target_schema,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "category": self.category,
            "disposition": self.disposition,
            "has_genai": self.has_genai,
            "apply_status": self.apply_status,
            "apply_error": self.apply_error,
            "action_items": [a.to_dict() for a in self.action_items],
            "source_ddl_ref": self.source_ddl_ref,
            "target_ddl_ref": self.target_ddl_ref,
        }


@dataclass
class ImportResult:
    """Everything parsed from one DMS SC project directory."""
    dms_sc_dir: str
    source_engine: str = ""
    target_engine: str = ""
    objects: List[DmsScObject] = field(default_factory=list)
    # action items that could not be attached to a parsed object (schema/column level)
    unmatched_action_items: Dict[str, List[ActionItem]] = field(default_factory=dict)

    def schemas(self) -> List[str]:
        seen = []
        for o in self.objects:
            s = (o.source_schema or "").upper()
            if s and s not in seen:
                seen.append(s)
        return seen

    def for_schema(self, schema: str) -> List[DmsScObject]:
        s = (schema or "").upper()
        return [o for o in self.objects if (o.source_schema or "").upper() == s]
