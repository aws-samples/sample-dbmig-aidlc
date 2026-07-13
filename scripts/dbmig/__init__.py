"""dbmig-aidlc — pure-Python database migration toolkit.

Supported engine pairs: Oracle and SQL Server (sources) → PostgreSQL and MySQL
(targets). Deterministic database work (connectivity, DDL extraction, apply, data
copy, reconciliation) runs standalone via engine adapters built on Python drivers
(``oracledb`` thin, ``python-tds``, ``psycopg`` v3, ``PyMySQL``).
Schema conversion is LLM-driven: the package extracts Oracle object-units and
builds prompt bundles with injected skill/playbook context; the Kiro
``db-migration-construction`` skill performs the actual conversion; the package
then applies the converted DDL to the target.

Entry point: ``python -m dbmig <command>``.
"""

__version__ = "0.2.0"
__all__ = ["__version__"]
