<!-- dbmig test-generation prompt
     object: FUNCTION DEMO.CALCULATE_DISCOUNT_PCT
     Write the test spec (YAML) to: tests/DEMO/function__calculate_discount_pct.test.yaml
     Then set status 'generated' in test-manifest-DEMO.yaml. -->

# Construction skill guidance

---
name: db-migration-construction
description: Construction phase (conversion) of an AI-DLC database migration. Use after the Inception migration plan is approved, or when the user asks to convert/translate a source database schema, tables, datatypes, views, or stored code (PL/SQL, T-SQL, etc.) to the target engine. Engine-agnostic across all supported pairs (Oracle or SQL Server → PostgreSQL or MySQL). The conversion is LLM-driven and YOU (Kiro) are the LLM: the dbmig Python tool extracts source object-units and writes prompt bundles, you convert each bundle to target DDL using the active pair's playbook references as context, then dbmig applies the DDL to the target. Writes artifacts to migrations/<project>/02-construction/.
---

# Construction — Conversion (LLM-driven; you are the LLM)

This is the **Construction** phase. Conversion is **not rule-based** — the `dbmig`
Python package does the deterministic work (extract object-units, write prompt bundles,
apply DDL, report errors), and **you (Kiro) perform the actual source→target conversion**
using the active pair's playbook references as your knowledge base.

The package never calls a hosted LLM. It runs with `provider: kiro` (hand-off mode).

## Active engine pair (read this first)

The framework supports multiple pairs. Determine the **active pair** from the connection
engines in `connections.yaml`: `<source>-to-<target>` (e.g. `oracle-to-postgresql`,
`oracle-to-mysql`, `sqlserver-to-postgresql`, `sqlserver-to-mysql`). Throughout this skill,
substitute that pair for `<pair>`:

- Knowledge base / playbook references: `skills/<pair>-playbook/references/...`
- Engine definition + datatype map: `engines/<pair>/`

The prompt bundles `dbmig` writes already inject the **correct** pair's context, so you
mostly read the bundle; open the pair's playbook topic files when you need more detail.

## The conversion loop

### 1. Prepare (dbmig extracts + builds prompts)
```bash
python -m dbmig convert-schema --schema <SCHEMA> --project <project>
# or a subset:
python -m dbmig convert-schema --schema <SCHEMA> --tables ORDERS,CUSTOMERS --project <project>
```
This extracts each **object-unit** (one table + its indexes + constraints (PK/UK/CHECK)
+ foreign keys + DML triggers + comments/grants), batches small tables together, and
writes:
- prompt bundles → `migrations/<project>/02-construction/prompts/<SCHEMA>/*.prompt.md`
- a manifest → `migrations/<project>/02-construction/manifest-<SCHEMA>.yaml` (one row per
  unit: `name, batch_id, prompt_file, output_file, status: pending`). Manifests are
  **schema-scoped**, so one `--project` can hold several schemas (migrate referenced schemas
  first so cross-schema foreign keys resolve at `--post-data`). Older single-schema runs with
  a plain `manifest.yaml` are still read as a fallback.

### 2. Convert (YOU do this — the core LLM step)
For each `pending` unit in the manifest:
1. Read its prompt bundle. It already injects the construction guidance, the active pair's
   datatype map, and the pair's playbook topic index. Open the specific
   `skills/<pair>-playbook/references/...` topic files the unit needs (datatypes,
   constraints, triggers, sequences/identity, indexes, etc.).
2. Convert the whole object-unit **holistically** to the **target** engine's DDL — choose
   the right types, index kinds, and constraint forms given the full unit; fold identifier
   case per the target's convention; and rewrite **source-specific constructs** flagged in
   the pair's playbook (e.g. Oracle `ROWNUM`/`DUAL`/`NVL`, SQL Server `TOP`/`IDENTITY`/
   `GETDATE()`/`ISNULL`). A batch prompt converts several tables — write each table's DDL
   to its own output file.
   - **Customer-specific knowledge wins.** Apply any rules under
     `skills/<pair>-playbook/references/customer-specific/` first — they OVERRIDE the general
     playbook (and the datatype map) on conflict. The prompt bundle already injects them at
     the top, labeled highest precedence.
3. **Write the target DDL** to the unit's `output_file`
   (`02-construction/ddl/<schema>/<table>.sql`). Return only SQL (fenced or plain).
4. Set that unit's `status` to `converted` in `manifest.yaml`.
5. Record notable decisions / risky constructs as SQL comments and in a short
   `02-construction/conversion-log.md`, citing the playbook reference used (traceability).

### 3. Apply (dbmig applies to the target — gated)
```bash
python -m dbmig apply-schema --schema <SCHEMA> --project <project>
```
- Applying DDL writes to the target — a **gated action**. Confirm before the first run.
- `apply-schema` is **status-aware**: it skips units already `applied` (so re-running after
  a fix never re-triggers "already exists"), and applies multi-pass so foreign keys to
  not-yet-created tables resolve on a later pass.
- **Foreign keys + triggers are deferred.** The default `apply-schema` applies tables,
  indexes, PK/UK/CHECK and trigger *functions*, but holds back `FOREIGN KEY` constraints and
  `CREATE TRIGGER` statements. Those are applied later by `apply-schema --post-data`, **after**
  `migrate-data` (Validation phase) — so enforced FKs don't dictate load order and row triggers
  don't rewrite the data being loaded. The deferred pass is tracked in a separate `post_status`
  field (independently idempotent).
- It writes `02-construction/apply_report.yaml` and updates each unit's status/attempts in
  the manifest. Use `--dry-run` to preview the DDL without executing it.

**Automated error-retry loop (minimize human-in-the-loop).** When a unit fails to apply,
`apply-schema` captures the **target database error** and writes a **remediation prompt** at
`02-construction/retries/<SCHEMA>/<unit>.retry.md` (original prompt + the failed DDL + the
exact error), enforcing `llm.max_retries` (default 3) per unit. Follow this loop:

1. Run `apply-schema`.
2. If the output contains **`RETRY_AVAILABLE`**: for each listed failed unit, read its
   `retries/<SCHEMA>/<unit>.retry.md`, produce **corrected** target DDL, overwrite the
   unit's `output_file`, then run `apply-schema` again. Repeat automatically.
3. Stop when apply reports **all units applied** (success) or **`MAX_RETRIES_EXHAUSTED`**
   (units that hit `max_retries` are marked `needs_human`).
4. Only on `MAX_RETRIES_EXHAUSTED` bring the human in: summarize the `needs_human` units and
   their `last_error`, and propose options (redesign, a `customer-specific/` override, or
   skipping the object).

Override the cap with `--max-retries N`, or target units with `--tables ORDERS,CUSTOMERS`.
Use `--code` to run the same loop for code objects.

### 4. Code objects (separate pass)
Stored code (packages, procedures, functions, types — PL/SQL or T-SQL depending on the
source) needs different context and often iterative refinement:
```bash
python -m dbmig convert-code --schema <SCHEMA> --project <project>   # writes code_prompts/ + code-manifest.yaml
# you convert each code object -> 02-construction/code/<schema>/*.sql, set status converted
python -m dbmig apply-schema --schema <SCHEMA> --project <project> --code
```
Constructs with no direct target equivalent (e.g. Oracle packages, SQL Server CLR/Service
Broker) are redesigned per the pair's playbook (see its `sql-plsql/` or `tsql/` references).
Expect convert → apply → test → refine cycles.

**Package-flattening naming conflicts (Oracle).** Packages are flattened to
`<package>_<subprogram>` routines. `convert-code` automatically checks (via `ALL_PROCEDURES`)
whether that underscore-join is unique and **warns + records `naming_conflict` items to
`follow-up.yaml`** when two different Oracle routines collapse onto the same name (e.g.
`BOOK_PKG.GET_X` and `BOOK.PKG_GET_X` both → `book_pkg_get_x`, or a package routine shadowing
a standalone). Resolve flagged collisions by using a distinct separator (e.g. the AWS SCT
`<package>$<subprogram>` style) or an explicit rename — see the pair's
`checks/package-naming.md`.

## Holistic, object-unit conversion (why)
Converting a table with its indexes, constraints, and triggers together lets you make
decisions a layer-by-layer pass cannot — e.g. picking an index type informed by a
constraint, or folding a simple trigger into a `CHECK`/`GENERATED` column. Always convert
the unit as a whole.

## Handling hard cases
- For Manual/Blocked items from Inception, propose the redesign, explain the tradeoff,
  get the user's decision, then implement. Don't silently approximate behavior — the
  Validation phase will test for equivalence and surface it.
- Leave clearly-commented TODOs for anything that needs human review.

## Gate
When the planned units are converted and applied, summarize: units converted/applied by
status (from the manifest + apply report), anything deferred/blocked, and where the DDL
lives. **Stop at the gate: "Approve the converted schema + code?"** Then hand off to
`db-migration-validation`.


---

# Oracle -> postgresql datatype reference (general default)

```yaml
# engines/oracle-to-postgresql/datatype-map.yaml
#
# Oracle -> PostgreSQL datatype mapping used during schema conversion.
# "notes" call out precision/behavioral differences the validation phase checks.

mappings:
  # Numbers
  - oracle: NUMBER(p,0)            # p <= 4
    postgresql: smallint
    when: "p between 1 and 4, scale 0"
  - oracle: NUMBER(p,0)            # 5 <= p <= 9
    postgresql: integer
    when: "p between 5 and 9, scale 0"
  - oracle: NUMBER(p,0)            # 10 <= p <= 18
    postgresql: bigint
    when: "p between 10 and 18, scale 0"
  - oracle: NUMBER(p,s)
    postgresql: numeric(p,s)
    when: "scale > 0 or p > 18"
  - oracle: NUMBER                 # no precision/scale
    postgresql: numeric
    notes: "Unconstrained NUMBER -> numeric (arbitrary precision). Watch performance vs bigint/double."
  - oracle: FLOAT(b)
    postgresql: double precision
    notes: "Oracle binary-precision FLOAT maps to double precision; validate rounding."
  - oracle: BINARY_FLOAT
    postgresql: real
  - oracle: BINARY_DOUBLE
    postgresql: double precision

  # Character
  - oracle: VARCHAR2(n CHAR)
    postgresql: varchar(n)
    notes: "PostgreSQL length is in characters by default — matches CHAR semantics."
  - oracle: VARCHAR2(n BYTE)
    postgresql: varchar(n)
    notes: "BYTE semantics differ under multibyte encodings; verify max length in UTF-8."
  - oracle: NVARCHAR2(n)
    postgresql: varchar(n)
  - oracle: CHAR(n)
    postgresql: char(n)
    notes: "Both blank-pad; trailing-space comparison semantics differ slightly."
  - oracle: NCHAR(n)
    postgresql: char(n)
  - oracle: CLOB
    postgresql: text
  - oracle: NCLOB
    postgresql: text
  - oracle: LONG
    postgresql: text
    notes: "Deprecated in Oracle; map to text."

  # Binary
  - oracle: BLOB
    postgresql: bytea
    notes: "bytea has practical size limits (~1GB) vs Oracle LOB; check large objects."
  - oracle: RAW(n)
    postgresql: bytea
  - oracle: LONG RAW
    postgresql: bytea

  # Date / time
  - oracle: DATE
    postgresql: timestamp(0)
    notes: "Oracle DATE includes time to seconds — map to timestamp, NOT date, to avoid losing time."
  - oracle: TIMESTAMP(p)
    postgresql: timestamp(p)
  - oracle: TIMESTAMP(p) WITH TIME ZONE
    postgresql: timestamptz(p)
  - oracle: TIMESTAMP(p) WITH LOCAL TIME ZONE
    postgresql: timestamptz(p)
    notes: "Behavioral difference around session time zone; validate conversions."
  - oracle: INTERVAL YEAR TO MONTH
    postgresql: interval
  - oracle: INTERVAL DAY TO SECOND
    postgresql: interval

  # Rowid / misc
  - oracle: ROWID
    postgresql: text
    notes: "No direct equivalent; ctid is not stable. Re-architect logic depending on ROWID."
  - oracle: UROWID
    postgresql: text
  - oracle: XMLTYPE
    postgresql: xml
  - oracle: "SDO_GEOMETRY"
    postgresql: geometry
    notes: "Requires PostGIS on the target."
  - oracle: BOOLEAN              # PL/SQL only in Oracle <23c
    postgresql: boolean
    notes: "Oracle SQL had no BOOLEAN before 23c; often stored as NUMBER(1)/CHAR(1) — confirm source representation."

# Identifier handling
identifiers:
  oracle_default_case: UPPER
  postgresql_default_case: lower
  recommendation: "Fold UPPER Oracle names to lower_case unquoted PG identifiers; avoid quoted mixed-case which forces quoting everywhere."

# Common gotchas validated in the testing phase
gotchas:
  - "Empty string '' = NULL in Oracle, but '' is NOT NULL in PostgreSQL."
  - "Oracle DATE arithmetic (date+1 = +1 day) differs from PG timestamp arithmetic (use interval)."
  - "NUMBER default scale rounding vs numeric exactness."
  - "Implicit type coercion is more permissive in Oracle than PostgreSQL."

```

---

# Playbook topic index — general guidance (open the referenced files under `skills/oracle-to-postgresql-playbook/references/` as needed; customer-specific rules above win on conflict)

# Configuration References — Oracle → Aurora PostgreSQL

Distilled from the AWS *Oracle to Aurora PostgreSQL Migration Playbook* (Configuration chapter). Reference only — test everything in a non-production environment first.

- [upgrades.md](upgrades.md) — Oracle minor/major version upgrade process vs. managed Aurora PostgreSQL upgrades (parameter groups, `reg*` type and prepared-transaction prerequisites, console/CLI steps).
- [alert-log-and-error-log.md](alert-log-and-error-log.md) — Oracle Alert Log (`alert<sid>.log`, ADR) vs. PostgreSQL error log (severity levels, RDS console access, `log_*` config params, SNS event notifications).
- [memory-sizing-and-buffers.md](memory-sizing-and-buffers.md) — Oracle SGA/PGA pools vs. PostgreSQL memory buffers (`shared_buffers`, `wal_buffers`, `work_mem`, etc.) and Aurora instance-class sizing.
- [instance-parameters-and-rds-parameter-groups.md](instance-parameters-and-rds-parameter-groups.md) — Oracle `ALTER SYSTEM`/SPFILE vs. Aurora cluster and database parameter groups, including AWS-optimized default formulas.
- [session-parameters.md](session-parameters.md) — Oracle `ALTER SESSION` vs. PostgreSQL `SET SESSION`/`SET LOCAL`, with a side-by-side parameter mapping.


# Customer-Specific Knowledge — HIGHEST PRECEDENCE

This folder holds knowledge about **this customer's own environment and application** —
their conventions, constraints, prior decisions, and any deviations from the generic AWS
playbook. It is intentionally empty of vendor content: you fill it in per engagement.

## Precedence rule

When converting or assessing objects, content in this folder **overrides** the general
playbook references (`../sql-plsql/`, `../tables-indexes/`, `../special-features/`, etc.)
**wherever the two conflict.** The general playbook is the default; customer-specific rules
are the authority for this customer.

The conversion tooling enforces this: `dbmig convert-schema` / `convert-code` inject every
file in this folder at the **top** of each prompt bundle, labeled as highest precedence,
ahead of the general playbook context. The `db-migration-construction` skill applies the
same ordering when it converts.

## What belongs here

Create one Markdown file per topic. Suggested files (all optional):

- `environment.md` — target setup: Aurora PostgreSQL version, extensions available
  (e.g. `pg_trgm`, `postgis`, `pg_cron`), instance class, network/SSL, region.
- `naming-conventions.md` — identifier casing, schema layout, table/column/constraint/index
  naming rules the customer requires (may differ from the playbook's lower_case default).
- `datatype-overrides.md` — customer mappings that override the generic datatype map
  (e.g. "Oracle `NUMBER(1)` flags map to `boolean`", "money columns use `numeric(19,4)`").
- `application-constraints.md` — app/ORM expectations (Hibernate dialect, sequence usage,
  case-sensitivity assumptions, queries that must not change shape).
- `decisions.md` — engagement decisions already made (what was deferred, what was approved,
  agreed redesigns for packages / ROWID logic / autonomous transactions).
- `forbidden.md` — things the customer explicitly disallows (extensions, features, patterns).

## Rules for writing these files

- Be specific and prescriptive — these are instructions, not background reading.
- State each rule so it can be applied directly to a single object's conversion.
- When a rule overrides the playbook, say so explicitly ("Override: …") so the intent is
  unambiguous at conversion time.
- Keep secrets out — this folder is committed with the repo. Reference systems by name, not
  credentials.

## Status

No customer files are present yet. Add files here at the start of an engagement. Until then,
conversion falls back entirely to the general playbook references.


# High Availability & Disaster Recovery — Reference Index

Distilled from the AWS *Oracle → Aurora PostgreSQL Migration Playbook* (HA/DR chapter). Reference only — test everything in a non-production environment first.

- [active-data-guard-and-replicas.md](active-data-guard-and-replicas.md) — Oracle Active Data Guard standby databases vs. Aurora read replicas / Multi-AZ (sync, delayed standby, and snapshot-standby gaps noted).
- [rac-and-aurora-architecture.md](rac-and-aurora-architecture.md) — Oracle RAC shared-disk Active-Active clustering vs. Aurora single-primary + read-replica architecture, with full feature comparison.
- [traffic-director-and-rds-proxy.md](traffic-director-and-rds-proxy.md) — Oracle Connection Manager Traffic Director mode vs. Amazon RDS Proxy for connection pooling and HA.
- [data-pump-and-pg-dump-restore.md](data-pump-and-pg-dump-restore.md) — Oracle Data Pump (expdp/impdp) vs. PostgreSQL pg_dump/pg_restore for logical export/import.
- [flashback-database-and-snapshots.md](flashback-database-and-snapshots.md) — Oracle Flashback Database point-in-time revert vs. Aurora snapshots and point-in-time restore (CLI + console).
- [flashback-table-and-snapshots.md](flashback-table-and-snapshots.md) — Oracle Flashback Table single-table rewind vs. Aurora snapshot restore + pg_dump/pg_restore table copy-back.
- [rman-and-rds-snapshots.md](rman-and-rds-snapshots.md) — Oracle RMAN backup/recovery (full, incremental, PITR, PDB) vs. Aurora automated/manual snapshots and PITR.
- [sqlloader-and-pg-dump-restore.md](sqlloader-and-pg-dump-restore.md) — Oracle SQL*Loader flat-file bulk loading vs. PostgreSQL COPY / load-from-S3 / pg_restore.


# Performance Tuning — Reference Index

Oracle → Aurora PostgreSQL migration references for performance tuning, distilled from the AWS Oracle→Aurora PostgreSQL Migration Playbook.

- [hints-and-query-planning.md](hints-and-query-planning.md) — Oracle's 60+ inline optimizer hints vs. PostgreSQL session-level query planning parameters (`ENABLE_SEQSCAN`, `ENABLE_NESTLOOP`, `SEQ_PAGE_COST`, `RANDOM_PAGE_COST`); manual conversion since PostgreSQL has no per-statement hints.
- [run-plans.md](run-plans.md) — Reading execution plans: Oracle `EXPLAIN PLAN`/`AUTOTRACE` vs. PostgreSQL `EXPLAIN`/`EXPLAIN ANALYZE`, operator mapping (`TABLE ACCESS FULL` → `Seq Scan`), and Aurora PostgreSQL Query Plan Management (QPM).
- [table-statistics.md](table-statistics.md) — Collecting optimizer statistics: Oracle `DBMS_STATS` and automatic collection vs. PostgreSQL `ANALYZE` and the autovacuum daemon, including sampling/granularity differences.


# Physical Storage — Reference Index

Distilled references from the AWS Oracle→Aurora PostgreSQL Migration Playbook (physical storage topics).

- [table-partitioning-and-inheritance.md](table-partitioning-and-inheritance.md) — Oracle hash/list/range/composite partitioning vs PostgreSQL declarative partitioning (PG 10/11+) and the pre-10 inheritance + trigger pattern; includes full SQL examples and a per-type support matrix. (Assisted)
- [sharding.md](sharding.md) — Oracle horizontal sharding across independent shard databases; not supported natively in PostgreSQL, requires re-architecture, DMS handles data movement. (Blocked)


# Security References — Oracle → Aurora PostgreSQL

Distilled reference pages from the AWS Oracle→Aurora PostgreSQL Migration Playbook (Security chapter).

| File | Summary |
|---|---|
| [tde-and-encryption.md](./tde-and-encryption.md) | Oracle Transparent Data Encryption (TDE) column/tablespace encryption vs. Amazon Aurora storage-level encryption via AWS KMS (AES-256), plus SSE-S3 overview. Conversion category: Manual. |
| [roles.md](./roles.md) | Oracle roles (common/local, 12c) vs. PostgreSQL cluster-global roles, with full Oracle→PostgreSQL command mapping table. Conversion category: Assisted. |
| [users.md](./users.md) | Oracle database users (common/local, user=schema, auth mechanisms) vs. PostgreSQL — no users, only login roles; schemas created separately. Conversion category: Assisted. |


# Special Features — Oracle → Aurora PostgreSQL Reference Index

Distilled from the AWS *Oracle to Aurora PostgreSQL Migration Playbook* (Special features chapter). Each file documents the Oracle behavior, the PostgreSQL/Aurora equivalent, and conversion notes with preserved SQL examples.

| File | Summary |
|---|---|
| [character-sets-and-encoding.md](character-sets-and-encoding.md) | Oracle character sets (VARCHAR2/NVARCHAR2, AL32UTF8/AL16UTF16) vs PostgreSQL encodings + locale; no NCHAR/UTF-16; changing encoding requires export/recreate/import. (Assisted) |
| [database-links-dblink-fdw.md](database-links-dblink-fdw.md) | Oracle DATABASE LINK vs PostgreSQL `dblink` and `postgres_fdw`; no permanent named links; plaintext credential and oracle_fdw-on-RDS caveats. (Manual) |
| [dbms-scheduler-and-lambda.md](dbms-scheduler-and-lambda.md) | Oracle DBMS_SCHEDULER (time/event/chained jobs) vs Aurora using CloudWatch + AWS Lambda. (Manual) |
| [external-tables-and-s3.md](external-tables-and-s3.md) | Oracle external tables (ORACLE_LOADER/DATAPUMP/HDFS/HIVE) vs Aurora `aws_s3` export/import functions; no external tables in PostgreSQL. (Manual) |
| [inline-views.md](inline-views.md) | Inline views/subqueries — fully compatible; PostgreSQL requires a mandatory alias on FROM-clause subqueries. (Automatic) |
| [json-support.md](json-support.md) | Oracle JSON (CLOB + IS JSON, dot notation) vs PostgreSQL JSON/JSONB operators and GIN indexing; application rewrite needed. (Assisted) |
| [materialized-views.md](materialized-views.md) | Oracle MViews (fast/complete refresh, MV logs, ON COMMIT) vs PostgreSQL complete-only refresh, trigger-driven auto-refresh, no DML. (Assisted) |
| [multitenant-architecture.md](multitenant-architecture.md) | Oracle CDB/PDB multitenant vs Aurora cluster + multiple databases / separate clusters; TEMPLATE cloning, logical replication. (Assisted) |
| [resource-manager-and-dedicated-clusters.md](resource-manager-and-dedicated-clusters.md) | Oracle Resource Manager (consumer groups/plans/directives) vs dedicated/right-sized Aurora clusters + pg_stat_activity/pg_locks scripting. (Manual/architectural) |
| [securefile-lobs-and-large-objects.md](securefile-lobs-and-large-objects.md) | Oracle SecureFile LOBs (compression/dedup/encryption) vs PostgreSQL BYTEA/TEXT + TOAST + KMS; SecureFiles unsupported. (Assisted) |
| [views.md](views.md) | Oracle views (simple/complex, CHECK OPTION, INSTEAD OF) vs PostgreSQL auto-updatable simple views and CASCADED/LOCAL CHECK OPTION. (Assisted) |
| [xml-db-and-xml-type.md](xml-db-and-xml-type.md) | Oracle XML DB (XMLType, XMLIndex, XQuery, SQL/XML functions) vs PostgreSQL xml type, xpath()/xmltable(); no XQuery or XSD validation. (Assisted) |
| [log-miner-and-logging.md](log-miner-and-logging.md) | Oracle Log Miner (redo logs, SQL_REDO/SQL_UNDO) vs PostgreSQL pg_stat_statements, statement logging, Aurora Performance Insights; no SQL_UNDO. (Manual) |


# SQL and PL/SQL Conversion References (Oracle → Aurora PostgreSQL)

Distilled from the AWS *Oracle to Aurora PostgreSQL Migration Playbook*. Each file covers one feature with conversion category, Oracle vs PostgreSQL syntax, and conversion notes.

| File | Conversion category | Summary |
|---|---|---|
| [single-row-and-aggregate-functions.md](single-row-and-aggregate-functions.md) | Assisted | Mapping of Oracle numeric/character/datetime/null/conversion/aggregate functions to PostgreSQL equivalents, with gotchas (`DECODE`, `NVL`, `LISTAGG`→`STRING_AGG`). |
| [create-table-as-select.md](create-table-as-select.md) | Automatic | CTAS is ANSI-compatible; migrates with no rewrite. PG adds `WITH NO DATA`, `UNLOGGED`, `IF NOT EXISTS`. |
| [common-table-expressions.md](common-table-expressions.md) | Automatic | `WITH` CTEs migrate directly; PG adds `WITH RECURSIVE` to replace Oracle `CONNECT BY`. |
| [identity-columns-and-serial.md](identity-columns-and-serial.md) | Assisted | Oracle 12c `IDENTITY` → PG `SERIAL` or (preferred) `GENERATED BY DEFAULT AS IDENTITY`; reset sequences after explicit inserts. |
| [insert-from-select.md](insert-from-select.md) | Assisted | `INSERT … SELECT` migrates directly; rewrite `LOG ERRORS`/`DBMS_ERRLOG` and subquery-insert forms using `ON CONFLICT`. |
| [multi-version-concurrency-control.md](multi-version-concurrency-control.md) | Automatic | MVCC/locking model matches Oracle; key difference is PG auto-commit and per-transaction isolation; lock examples and `pg_locks` monitoring. |
| [merge-statement.md](merge-statement.md) | Manual | No `MERGE` in PG 13; emulate upsert with `INSERT … ON CONFLICT DO UPDATE` (native MERGE exists in PG 15+). |
| [olap-and-window-functions.md](olap-and-window-functions.md) | Assisted | Oracle OLAP → PG window functions (identical syntax, differing return types); rewrite `CONNECT BY` / hierarchical functions. |
| [sequences.md](sequences.md) | Assisted | `CREATE SEQUENCE` mostly compatible; mechanical rewrites (`NOMAXVALUE`→`NO MAXVALUE`), dot syntax → `NEXTVAL()/CURRVAL()`; no 18c scalable sequences. |
| [transaction-model.md](transaction-model.md) | Assisted | ACID/isolation levels compared; PG read-committed default matches Oracle; no `SAVEPOINT` inside functions; no true nested transactions. |
| [anonymous-block-and-do.md](anonymous-block-and-do.md) | Assisted | Oracle anonymous `BEGIN…END;/` → PG `DO $$ … $$;`; declare loop vars, `DBMS_OUTPUT`→`RAISE`. |
| [cursors.md](cursors.md) | Assisted | PL/SQL cursors → PL/pgSQL `refcursor`; attribute mapping (`%NOTFOUND`→`NOT FOUND`); no `REF CURSOR` type, `%ISOPEN`, `%BULK_*`. |
| [dbms-output-and-raise.md](dbms-output-and-raise.md) | Manual | `DBMS_OUTPUT.PUT_LINE` → `RAISE NOTICE`; severity levels; `SQLCODE`→`SQLSTATE`; no buffer/`GET_LINE` model. |
| [dbms-random-and-random.md](dbms-random-and-random.md) | Manual | `DBMS_RANDOM.VALUE/STRING` → `random()` / `md5(random()::text)` / custom `random_string()` function. |
| [dbms-sql-dynamic-execution.md](dbms-sql-dynamic-execution.md) | Manual | No `DBMS_SQL` equivalent; redesign with `EXECUTE`/`OPEN refcur FOR EXECUTE format(...)` and `format()` `%I`/`%L`. |
| [execute-immediate-and-prepare.md](execute-immediate-and-prepare.md) | Assisted | `EXECUTE IMMEDIATE` → PL/pgSQL `EXECUTE` (binds `:1`→`$1`, `format()` for identifiers); `PREPARE`/`EXECUTE` for reuse. |
| [procedures-and-functions.md](procedures-and-functions.md) | Assisted | Oracle procedures/functions → PG `CREATE FUNCTION` (PG 13); packages have no equivalent (SCT uses `pkg$member`); `SELECT INTO STRICT`. |
| [user-defined-functions.md](user-defined-functions.md) | Assisted | Oracle UDFs → PG `CREATE FUNCTION … LANGUAGE PLPGSQL`; drop `FROM dual`, `RETURN`→`RETURNS`, `SYSDATE`→`NOW()`. |
| [utl-file.md](utl-file.md) | Blocked | No `UTL_FILE` equivalent; move file I/O to app/ETL layer, `COPY`, or `aws_s3` extension. |
| [utl-mail-smtp-and-ses.md](utl-mail-smtp-and-ses.md) | Manual | No in-database email; replace `UTL_MAIL`/`UTL_SMTP` with scheduled Lambda + Amazon SES (or RDS event notifications). |


# Tables and Indexes — Reference Index

Oracle → Aurora PostgreSQL conversion references distilled from the AWS Oracle→Aurora PostgreSQL Migration Playbook.

## Tables
- [case-sensitivity.md](case-sensitivity.md) — Oracle names are case-insensitive; PostgreSQL folds unquoted names to lower-case and is case-sensitive (use lower-case via DMS transforms).
- [common-data-types.md](common-data-types.md) — Oracle↔PostgreSQL data type mapping tables, BYTE/CHAR semantics, and AWS SCT example; BFILE/ROWID/UROWID need manual handling.
- [read-only-tables-and-replicas.md](read-only-tables-and-replicas.md) — Oracle READ ONLY tables/partitions vs PostgreSQL workarounds (read-only role, database, or trigger).
- [table-constraints.md](table-constraints.md) — PK/FK/UNIQUE/CHECK/NOT NULL mapping; PostgreSQL adds ON UPDATE and EXCLUDE, drops REF and view constraints.
- [temporary-tables.md](temporary-tables.md) — Oracle GLOBAL temp tables vs PostgreSQL session-local temp tables; reversed ON COMMIT default.
- [triggers.md](triggers.md) — Oracle inline-body triggers vs PostgreSQL function+trigger model; no system/DB-event triggers in PostgreSQL.
- [tablespaces-and-data-files.md](tablespaces-and-data-files.md) — Tablespace/data-file concepts; Aurora auto-manages files under /rdsdbdata/tablespaces/.
- [user-defined-types.md](user-defined-types.md) — Oracle OBJECT types vs PostgreSQL composite/enum/range/array types; no AS OBJECT or CREATE OR REPLACE TYPE.
- [unused-columns-and-alter-table.md](unused-columns-and-alter-table.md) — Oracle SET UNUSED/DROP UNUSED vs PostgreSQL DROP COLUMN + VACUUM FULL.
- [virtual-columns.md](virtual-columns.md) — Oracle virtual columns vs PostgreSQL 12+ generated columns, or views/functions/triggers + expression indexes.

## Indexes
- [indexes-summary.md](indexes-summary.md) — Overall index type/feature mapping and CREATE/ALTER/REINDEX DDL equivalents.
- [btree-indexes.md](btree-indexes.md) — B-tree indexes; direct 1:1 conversion (default in both).
- [bitmap-indexes.md](bitmap-indexes.md) — Oracle bitmap indexes have no PostgreSQL equivalent; consider BRIN.
- [composite-multicolumn-indexes.md](composite-multicolumn-indexes.md) — Composite/multicolumn indexes; identical syntax, up to 32 columns.
- [function-based-expression-indexes.md](function-based-expression-indexes.md) — Oracle function-based → PostgreSQL expression indexes (single-column only); plus partial indexes.
- [invisible-indexes.md](invisible-indexes.md) — Oracle invisible indexes; no equivalent in Aurora PostgreSQL.
- [index-organized-and-cluster-tables.md](index-organized-and-cluster-tables.md) — Oracle IOT vs PostgreSQL CLUSTER (one-time, non-persistent sort).
- [partitioned-indexes.md](partitioned-indexes.md) — Oracle local/global partitioned indexes vs PostgreSQL per-partition indexes (no global index).
- [automatic-indexing.md](automatic-indexing.md) — Oracle 19c auto indexing; no Aurora equivalent (Dexter/HypoPG unsupported), diagnostic queries provided.


# Tools & Services — Reference Index

Distilled from the AWS *Oracle Database 19c to Amazon Aurora PostgreSQL Migration Playbook* (Tools and services chapter). Reference only — test everything in a non-production environment first.

| File | Summary |
|---|---|
| [native-tools.md](native-tools.md) | **Informational.** Native clients (`sqlplus`/SQLcl, `psql`/`pg_dump`) for manual inspection. dbmig does NOT use them — it connects via Python drivers (oracledb thin + psycopg). |
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool — Java utility that connects to source/target, assesses the Oracle schema, and auto-converts objects to Aurora PostgreSQL; full download/configure/new-project walkthrough. |
| [sct-action-code-index.md](sct-action-code-index.md) | Automation-level legend (★ ratings) plus the full per-topic AWS SCT action-code catalog (SQL, tables, data types, cursors, triggers, sequences, views, UDTs, merge, matviews, hints, DB links, indexes, partitioning, OLAP, etc.). |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service — managed data migration/replication with near-zero source downtime; homogeneous and heterogeneous migrations, CDC, KMS/SSL/Secrets Manager security. Pairs with SCT (SCT=schema, DMS=data). |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts — managed RDS (SQL Server/MySQL/PostgreSQL) on premises for hybrid/low-latency/data-residency needs. Note: NOT supported with Aurora. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy — fully managed connection-pooling proxy; cuts failover time ~66%, integrates with Secrets Manager/IAM, no app code changes; GA for Aurora/RDS MySQL & PostgreSQL. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | Amazon Aurora Serverless v1 — on-demand autoscaling Aurora capacity for intermittent/unpredictable workloads; per-second billing, always-encrypted storage, scaling thresholds and pause/resume behavior. |


=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove the converted PostgreSQL (Aurora PostgreSQL compatible) function `DEMO.CALCULATE_DISCOUNT_PCT` behaves the same as the Oracle source: same input → same return value (functions) or same net effect (procedures). Tests will run on BOTH engines and the results compared.

Produce a test specification as YAML with this exact shape, written to the
object's output file. Use ONLY real values taken from the sampled data below so
the tests run against rows that actually exist.

For a FUNCTION (compare the return value for the same inputs on both engines):

    object: <NAME>
    schema: <SCHEMA>
    type: function
    notes: <how inputs were chosen from real data>
    cases:
      - id: c1
        description: <what this case covers>
        source_sql: "SELECT <schema>.<fn>(<real args>) FROM dual"
        target_sql: "SELECT <schema>.<fn>(<real args>)"
        compare: scalar          # scalar | resultset

For a PROCEDURE (no return value — verify the NET EFFECT is identical). YOU decide
which probe queries capture the procedure's effect (the rows/columns/aggregates it
changes); the runner snapshots each probe BEFORE and AFTER the call on each engine
and compares the delta (after - before) across source and target:

    object: <NAME>
    schema: <SCHEMA>
    type: procedure
    notes: <which tables/columns the procedure affects and why these probes verify it>
    cases:
      - id: c1
        description: <what this case covers>
        call_source: "BEGIN <schema>.<proc>(<real args>); END;"
        call_target: "CALL <schema>.<proc>(<real args>)"
        verify:
          - name: <probe name>
            source_sql: "SELECT <agg/col> FROM <schema>.<table> WHERE <real key>"
            target_sql: "SELECT <agg/col> FROM <schema>.<table> WHERE <real key>"

Rules:
- Every test runs inside a transaction that is ROLLED BACK afterward — safe to run.
- Pick a few representative cases (typical, boundary, NULL/edge) using real data.
- Probe queries must be deterministic and return a single scalar each.
- For packages, generate cases for the public subprograms a caller would use.
- Write source_sql / call_source in the SOURCE dialect and target_sql / call_target
  in the TARGET dialect (e.g. Oracle `... FROM dual` / `BEGIN p(); END;`, SQL Server
  `EXEC p ...`, PostgreSQL `SELECT ...` / `CALL p(...)`).


--- SOURCE (FUNCTION) — DEMO.CALCULATE_DISCOUNT_PCT ---
CREATE OR REPLACE EDITIONABLE FUNCTION "DEMO"."CALCULATE_DISCOUNT_PCT" (
    p_original_price NUMBER,
    p_discounted_price NUMBER
) RETURN NUMBER 
DETERMINISTIC
PARALLEL_ENABLE
IS
BEGIN
    IF p_original_price = 0 THEN
        RETURN 0;
    END IF;
    RETURN ROUND(((p_original_price - p_discounted_price) / p_original_price) * 100, 2);
END;

--- SAMPLED REAL DATA (use these actual values) ---
### ADDRESSES  (columns: ID, ADDRESS_LINE1, ADDRESS_LINE2, ADDRESS_TYPE, CITY, STATE, POSTAL_CODE, COUNTRY, CUSTOMER_ID, IS_DEFAULT)
  1 | 123 Main St | Apt 4B |  | Seattle | WA | 98101 | USA | 1 | 1
  2 | 456 Oak Ave |  |  | Portland | OR | 97205 | USA | 2 | 1
  3 | 789 Pine Rd |  |  | San Francisco | CA | 94102 | USA | 3 | 1
### BOOKS  (columns: ID, TITLE, AUTHOR, ISBN, DESCRIPTION, PUBLISH_DATE, YEAR, CREATED_ON, UPDATED_ON, CREATED_BY, GENRE_ID, PUBLISHER_ID, BOOK_TYPE_ID, SEARCH_TEXT)
  43 | The Night Circus | Erin Morgenstern | 9780385534635 | The circus arrives without warning, appearing at night and open only from sunset… |  |  | 2026-06-28 09:33:22.253283 |  | system | 6 | 5 | 1 | the night circus erin morgenstern 9780385534635
  44 | Mexican Gothic | Silvia Moreno-Garcia | 9780525620785 | When socialite Noemí receives a frantic letter from her newly-wed cousin begging… |  |  | 2026-06-28 09:33:22.263957 |  | system | 6 | 6 | 2 | mexican gothic silvia moreno-garcia 9780525620785
  45 | A Darker Shade of Magic | V.E. Schwab | 9780765387561 | Kell is one of the last Antari—magicians with the rare ability to travel between… |  |  | 2026-06-28 09:33:22.280182 |  | system | 6 | 7 | 1 | a darker shade of magic v.e. schwab 9780765387561
### BOOKS_COVER  (columns: BOOK_ID, COVER_IMAGE, CONTENT_TYPE, FILE_NAME, CREATED_ON, UPDATED_ON)
  1 | <binary 111650 bytes> | image/png | apocalypse.png | 2026-06-28 09:33:22.711072 | 2026-06-28 09:33:22.711072
  2 | <binary 115224 bytes> | image/png | childrenofiron.png | 2026-01-14 11:27:01.332299 | 2026-01-14 11:27:31.022000
  3 | <binary 91933 bytes> | image/png | goldinthedark.png | 2026-01-14 11:27:01.332299 | 2026-01-14 11:27:31.028000
### BOOK_TYPES  (columns: ID, CREATED_ON, DESCRIPTION, NAME, UPDATED_ON)
  1 |  | Book with a rigid binding | Hardcover | 
  2 |  | Book with a flexible paper binding, higher quality | Trade Paperback | 
  3 |  | Smaller format paperback book | Mass Market Paperback | 
### CONDITIONS  (columns: ID, CREATED_ON, DESCRIPTION, NAME, UPDATED_ON)
  1 |  | Brand new, never used, in perfect condition | New | 
  2 |  | Looks new but may have been read once or twice | Like New | 
  3 |  | Shows some signs of wear, may have markings | Good | 
### CUSTOMERS  (columns: ID, USERNAME, EMAIL, FIRST_NAME, LAST_NAME, PHONE_NUMBER, PASSWORD_HASH, SUB, DATE_OF_BIRTH, CREATED_ON, EMAIL_VERIFIED, ROLE, ACCOUNT_EXPIRED, CREDENTIALS_EXPIRED, ACCOUNT_LOCKED, LAST_LOGIN)
  1 | admin | admin@example.com | Admin | User | 555-0188 | <redacted> |  | 1980-01-01 00:00:00 | 2026-06-28 09:33:21.579671 | 1 | ADMIN | 0 | 0 | 0 | 
  2 | johndoe | john.doe@example.com | John | Doe | 555-0123 | <redacted> | auth0|123456 | 1985-05-15 00:00:00 | 2026-06-28 09:33:21.590830 | 1 | USER | 0 | 0 | 0 | 
  3 | janedoe | jane.doe@example.com | Jane | Doe | 555-0156 | <redacted> | auth0|234567 | 1990-10-20 00:00:00 | 2026-06-28 09:33:21.600432 | 1 | USER | 0 | 0 | 0 | 
### GENRES  (columns: ID, CREATED_ON, DESCRIPTION, NAME, UPDATED_ON)
  1 |  | Non-fiction account of someone's life | Biographies | 
  2 |  | Books for children | Children's Books | 
  3 |  | Non-fiction about past events | History | 
### LISTINGS  (columns: ID, BOOK_ID, SELLER_ID, PRICE, QUANTITY, CONDITION_ID, STATUS, LISTING_TYPE, ADMIN_NOTES, PROCESSED_AT, PROCESSED_BY, IS_FEATURED, IS_BESTSELLER, IS_NEW_ARRIVAL, CREATED_ON, UPDATED_ON)
  1 | 1 | 1 | 10.95 | 25 | 2 | 1 | SYSTEM |  |  |  | 1 | 0 | 1 | 2026-06-28 09:33:22.376331 | 
  2 | 2 | 1 | 13.95 | 3 | 3 | 1 | SYSTEM |  |  |  | 0 | 1 | 0 | 2026-06-28 09:33:22.382530 | 
  3 | 3 | 1 | 6.5 | 10 | 1 | 1 | SYSTEM |  |  |  | 1 | 1 | 0 | 2026-06-28 09:33:22.388200 | 
