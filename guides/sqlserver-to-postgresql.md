# Migration Guide — SQL Server → PostgreSQL

> **Engine pair:** `sqlserver` (source) → `postgresql` (target, Aurora PostgreSQL compatible)
> **Engine definition:** [`engines/sqlserver-to-postgresql/`](../engines/sqlserver-to-postgresql/)
> **Playbook:** [`skills/sqlserver-to-postgresql-playbook/`](../skills/sqlserver-to-postgresql-playbook/)
>
> One of several engine-pair guides — see the [guides index](README.md). Orchestration, the
> `dbmig` CLI, and the AI-DLC lifecycle are identical across pairs; only the engine adapter,
> the playbook references, and the source driver differ. SQL Server is the framework's first
> non-Oracle **source**.

A step-by-step guide to migrating a **Microsoft SQL Server** database to **PostgreSQL**
(Aurora PostgreSQL compatible) with **dbmig-aidlc**. The `dbmig` Python package does the
deterministic work; **Kiro performs the schema/T-SQL conversion** via the
`db-migration-construction` skill (the LLM is Kiro).

## 1. Prerequisites

- **Python 3.9+**; network access to the source SQL Server and target PostgreSQL.
- Install deps (pure-Python drivers — no native clients, no `sqlcmd`/`bcp`/`psql`):
  ```bash
  pip install -r scripts/requirements.txt   # oracledb, psycopg, pymysql, python-tds, pyyaml
  ```
- Run commands from the **repository root**.

## 2. Configure connections

```bash
cp templates/connections.example.yaml connections.yaml
cp templates/migration-config.example.yaml migration-config.yaml
```

Set the source to SQL Server (git-ignored files; use `${ENV_VAR}` for secrets):

```yaml
source:
  engine: sqlserver        # sqlserver | mssql | sql-server
  host: ${MSSQL_HOST}
  port: 1433
  database: ${MSSQL_DATABASE}
  username: ${MSSQL_USER}
  password: ${MSSQL_PASSWORD}

target:
  engine: postgresql
  host: ${PG_HOST}
  port: 5432
  database: ${PG_DATABASE}
  username: ${PG_USER}
  password: ${PG_PASSWORD}
  sslmode: require
```

The engine pair is detected automatically, so conversion uses the **SQL Server → PostgreSQL**
datatype map and the **sqlserver-to-postgresql-playbook** references. The SQL Server schema
is typically `dbo` — pass it as `--schema dbo`.

## 3. Run the migration

Conversationally: in Kiro say *"start a database migration from SQL Server to PostgreSQL"* —
the orchestrator runs the phases with approval gates. Or drive the CLI:

```bash
python -m dbmig test-connection --side both
python -m dbmig inventory       --schema dbo --project myproject

# Construction — Kiro converts each object-unit to PostgreSQL DDL, then apply (auto retry)
python -m dbmig convert-schema  --schema dbo --project myproject
python -m dbmig apply-schema    --schema dbo --project myproject
python -m dbmig convert-code    --schema dbo --project myproject   # procedures/functions/views
python -m dbmig apply-schema    --schema dbo --project myproject --code

# Data + validation (foreign keys + triggers are deferred to --post-data, after the load)
python -m dbmig migrate-data    --schema dbo --workers 8 --project myproject
python -m dbmig apply-schema    --schema dbo --project myproject --post-data
python -m dbmig compare         --schema dbo --project myproject
python -m dbmig gen-tests       --schema dbo --project myproject
python -m dbmig run-tests       --schema dbo --project myproject
```

The conversion hand-off, object-unit grouping, multi-pass apply, **error-retry loop**,
**silent/interactive run modes**, the follow-up log, and **equivalence testing** all work
exactly as in the [Oracle → PostgreSQL guide](oracle-to-postgresql.md) §5–§7. **Foreign keys
and triggers are deferred** and applied by `apply-schema --post-data` after the load; data is
loaded in **foreign-key dependency order** and identity sequences are reset afterward
(OPG guide §5.3). Data is loaded via the PostgreSQL COPY protocol; for production-scale
movement use AWS DMS (`testing.data_load: dms`).

### How the SQL Server source DDL is obtained
SQL Server has no `DBMS_METADATA`-style DDL generator. The `SQLServerEngine` adapter
**reconstructs each object-unit's DDL from the system catalogs** (`INFORMATION_SCHEMA` +
`sys.*`): a `CREATE TABLE` from column metadata, plus PK/UNIQUE/FK/CHECK constraints,
secondary indexes, and triggers. Code objects (procedures, functions, views) come from
`OBJECT_DEFINITION` / `sys.sql_modules`. This reconstructed DDL is the **context Kiro
converts** — faithful to the source, not necessarily byte-identical to the original script.

## 4. SQL Server-specific things to expect

The conversion (Kiro, using the SQL Server playbook + datatype map) accounts for these; the
validation phase tests for them:

- **Schema = `dbo`** by default → a PostgreSQL schema; fold mixed-case identifiers to
  lower_case.
- **Case sensitivity**: SQL Server is usually case-insensitive; PostgreSQL is case-sensitive
  — verify string comparisons / `LIKE` / `ORDER BY` (consider `citext` or `lower()`).
- **No CLUSTERED index** — a clustered PK becomes a normal PG primary key (B-tree).
- **IDENTITY** → `GENERATED ... AS IDENTITY` or sequences; the sequence is reset
  automatically after the data load.
- **T-SQL → PL/pgSQL** for procedures/functions/triggers; `@@IDENTITY`/`SCOPE_IDENTITY()` →
  `RETURNING`/`currval`; `TRY/CATCH` → `BEGIN ... EXCEPTION`.
- **Datatypes**: `money`→`numeric(19,4)`, `datetime`→`timestamp(3)`, `bit`→`boolean`,
  `uniqueidentifier`→`uuid`, `nvarchar(max)`→`text`; **`rowversion`/`timestamp` is binary,
  not a datetime**.
- **Common functions**: `GETDATE()`→`now()`, `ISNULL`→`COALESCE`, `LEN`→`length`,
  `TOP n`→`LIMIT`, `+` concat → `||`, `CHARINDEX`→`position`.
- **No equivalent / redesign**: CLR, Service Broker, linked servers (use `postgres_fdw`),
  full-text search (use `tsvector`/`pg_trgm`), columnstore indexes, `hierarchyid`,
  `sql_variant`.
- DDL and procedures that `COMMIT` internally can't be rolled back during testing — test
  those only against a disposable target.

## 4.1 Lessons from a real AdventureWorks run

A live migration of AdventureWorks `Person` + `Sales` (32 tables / ~395k rows / 6 views) to
Aurora PostgreSQL surfaced these practical points:

- **Multiple schemas in one project.** Manifests are **schema-scoped**
  (`manifest-<SCHEMA>.yaml`, `code-manifest-<SCHEMA>.yaml`,
  `test-manifest-<SCHEMA>.yaml`), so you can run the whole lifecycle for several schemas
  under one `--project` without them overwriting each other. Migrate **referenced schemas
  first** (e.g. `Person` before `Sales`) so cross-schema foreign keys resolve at the
  `--post-data` step.
- **Computed columns** (`SalesOrderHeader.SalesOrderNumber`/`TotalDue`,
  `SalesOrderDetail.LineTotal`) are reconstructed with a `-- computed in source: <expr>`
  annotation. Migrate them as **stored values** (a plain column — `COPY` loads the computed
  result from the source) *or* convert to a PostgreSQL `GENERATED ALWAYS AS (...) STORED`
  column — but **not** generated if you intend to `COPY` into it (PostgreSQL rejects explicit
  values for `GENERATED ALWAYS`). The default run loads them as plain columns.
- **XML columns** (`Person.Demographics`, `Store.Demographics`) map to `xml` and copy
  verbatim; converting the *views* that shred them uses `xpath()` with an explicit namespace
  prefix — see the playbook `tsql/json-and-xml.md`.
- **`geography`/`geometry`** and **`hierarchyid`** arrive from the driver as opaque binary, so
  `migrate-data` converts them to portable **text** at read time (`geography`/`geometry` →
  `STAsText()` WKT, `hierarchyid` → `ToString()` path like `/1/2/`); map the target column to
  `text` (or PostGIS `geography` if you need spatial ops). AdventureWorks `Person.Address.SpatialLocation`
  loaded as WKT text and `HumanResources.Employee.OrganizationNode` as a path string this way.
  Use `--exclude` to skip a table you intend to load with custom handling instead.
- **Reserved-word identifiers** (e.g. `SalesTerritory.[Group]`) must be quoted in the target
  DDL (`"group"`); the data loader lowercases and quotes columns automatically.
- **Out-of-scope dependencies when migrating a subset.** Foreign keys and triggers that
  reference schemas you are *not* migrating (here `Production`, `HumanResources`, `Purchasing`,
  `dbo`) should be **omitted and flagged** rather than applied — they would fail at
  `--post-data`. Two AdventureWorks triggers that write to `Production.TransactionHistory` /
  run XML `.modify` were left out and noted for manual rework.

## 5. Reference

- Datatype mapping: [`engines/sqlserver-to-postgresql/datatype-map.yaml`](../engines/sqlserver-to-postgresql/datatype-map.yaml)
- Equivalence-testing spec: [`engines/sqlserver-to-postgresql/checks/equivalence-spec.md`](../engines/sqlserver-to-postgresql/checks/equivalence-spec.md)
- Conversion knowledge base: [`skills/sqlserver-to-postgresql-playbook/`](../skills/sqlserver-to-postgresql-playbook/)
- Command reference, run modes, follow-up, workspace artifacts, troubleshooting, safety:
  see the [Oracle → PostgreSQL guide](oracle-to-postgresql.md) §9–§12 (identical, with
  `sqlserver`/`1433` source engine values and `--schema dbo`).

> Reference only — the playbook references are distilled from the AWS *Microsoft SQL Server
> 2019 to Amazon Aurora PostgreSQL Migration Playbook*. Test everything in a non-production
> environment first.
