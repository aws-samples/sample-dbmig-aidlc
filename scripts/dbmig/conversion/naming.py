"""Detect naming conflicts created by flattening Oracle packages into PostgreSQL.

PostgreSQL has no packages, so the convention is to flatten each package
subprogram into ``<package>_<subprogram>`` (lower-cased). Joining with an
underscore is readable but **not injective**: because both package and
subprogram names may themselves contain underscores, two different Oracle
objects can collapse onto the same PostgreSQL name. Examples:

    package ``BOOK_PKG`` proc ``GET_X``   ->  book_pkg_get_x
    package ``BOOK``     proc ``PKG_GET_X`` ->  book_pkg_get_x   # COLLISION

    package ``AUDIT`` proc ``LOG``  ->  audit_log
    standalone function ``AUDIT_LOG`` ->  audit_log              # shadows standalone

This module flags those cases so they can be disambiguated (a distinct
separator such as ``$`` — the AWS SCT style — or an explicit rename) before the
conversion is trusted.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional


def flatten_name(package: Optional[str], name: str, separator: str = "_") -> str:
    """PostgreSQL routine name for an Oracle routine under the flatten convention."""
    if package:
        return f"{package}{separator}{name}".lower()
    return name.lower()


def _label(package: Optional[str], name: str) -> str:
    return f"{package}.{name}" if package else f"(standalone) {name}"


def find_flatten_conflicts(routines: List[Dict],
                           separator: str = "_") -> List[Dict]:
    """Return conflicts produced by flattening ``routines`` with ``separator``.

    ``routines`` is a list of dicts with keys ``package`` (str or None for a
    standalone routine), ``name`` (subprogram/routine name), and optionally
    ``overload``. The result is a list of conflict dicts, each with:

    - ``flattened``  — the colliding PostgreSQL name
    - ``kind``       — ``"collision"`` (different Oracle objects collide; must
                       fix) or ``"overload"`` (same Oracle subprogram with
                       multiple overloads; allowed in PostgreSQL only if the
                       argument signatures differ — review)
    - ``involves_standalone`` — True if a standalone routine is one of the colliders
    - ``severity``   — ``"high"`` for collisions, ``"medium"`` for overloads
    - ``sources``    — human-readable list of the Oracle routines involved
    - ``overloads``  — (overload kind only) how many overloads share the name
    """
    groups: "OrderedDict[str, list]" = OrderedDict()
    for r in routines:
        flat = flatten_name(r.get("package"), r["name"], separator)
        groups.setdefault(flat, []).append(r)

    conflicts: List[Dict] = []
    for flat in sorted(groups):
        members = groups[flat]
        # Group members by their distinct Oracle identity (package, name).
        identities: "OrderedDict[tuple, list]" = OrderedDict()
        for m in members:
            identities.setdefault((m.get("package"), m["name"]), []).append(m)

        if len(identities) > 1:
            # Different Oracle objects collapse to the same PostgreSQL name.
            involves_standalone = any(pkg is None for pkg, _ in identities)
            conflicts.append({
                "flattened": flat,
                "kind": "collision",
                "severity": "high",
                "involves_standalone": involves_standalone,
                "sources": [_label(pkg, nm) for pkg, nm in identities],
            })
        else:
            (pkg, nm), ms = next(iter(identities.items()))
            if len(ms) > 1:  # same subprogram, multiple overloads
                conflicts.append({
                    "flattened": flat,
                    "kind": "overload",
                    "severity": "medium",
                    "involves_standalone": pkg is None,
                    "sources": [_label(pkg, nm)],
                    "overloads": len(ms),
                })
    return conflicts
