"""Parsing and classification for existing AWS DMS Schema Conversion (DMS SC) projects.

A DMS SC project is a flat tree of JSON node files (a source ``s-<id>/`` tree and a
target ``t-<id>/`` tree) plus catalogs under ``action-items/`` and apply results under
``apply-result/``. This package reads such a project **without any database access** and
produces a normalized object model that the ``import-dms-sc`` command turns into dbmig
manifests, a mapping sidecar, and an ACCEPT/VERIFY/MANUAL classification report.

See ``docs/dms-sc-import-design.md``. Parsing conventions follow the reference
implementation in ``sample-mma-test-manager`` (``S3LoaderService``): match source<->target
by source node id via ``synchronization_object``, key objects by node id (so overloaded
routines stay distinct), and skip container/folder meta-types.
"""
from .model import ActionItem, DmsScObject, ImportResult
from .parser import parse_project
from .classify import classify, ACCEPT, VERIFY, MANUAL
from . import verification

__all__ = [
    "ActionItem", "DmsScObject", "ImportResult",
    "parse_project", "classify", "ACCEPT", "VERIFY", "MANUAL",
    "verification",
]
