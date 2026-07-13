<!-- dbmig test-generation prompt
     object: VIEW HUMANRESOURCES.vJobCandidateEducation
     Write the test spec (YAML) to: tests/HUMANRESOURCES/view__vjobcandidateeducation.test.yaml
     Then set status 'generated' in test-manifest-HUMANRESOURCES.yaml. -->

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

# SQL Server -> postgresql datatype reference (general default)

```yaml
# engines/sqlserver-to-postgresql/datatype-map.yaml
#
# SQL Server -> PostgreSQL datatype mapping used as conversion context (not rules).
# "notes" call out precision/behavioral differences the validation phase checks.

mappings:
  # Integers
  - sqlserver: bit
    postgresql: boolean
    notes: "SQL Server bit is 0/1/NULL; map to boolean (or smallint if app expects 0/1)."
  - sqlserver: tinyint
    postgresql: smallint
    notes: "SQL Server tinyint is 0-255 unsigned; PostgreSQL has no tinyint — smallint."
  - sqlserver: smallint
    postgresql: smallint
  - sqlserver: int
    postgresql: integer
  - sqlserver: bigint
    postgresql: bigint

  # Exact / approximate numerics
  - sqlserver: decimal(p,s)
    postgresql: numeric(p,s)
  - sqlserver: numeric(p,s)
    postgresql: numeric(p,s)
  - sqlserver: money
    postgresql: numeric(19,4)
    notes: "Map money/smallmoney to numeric(19,4); never float."
  - sqlserver: smallmoney
    postgresql: numeric(10,4)
  - sqlserver: float(n)
    postgresql: double precision
  - sqlserver: real
    postgresql: real

  # Character
  - sqlserver: char(n)
    postgresql: char(n)
  - sqlserver: varchar(n)
    postgresql: varchar(n)
  - sqlserver: varchar(max)
    postgresql: text
  - sqlserver: nchar(n)
    postgresql: char(n)
    notes: "Use UTF-8 database encoding; no separate national type in PostgreSQL."
  - sqlserver: nvarchar(n)
    postgresql: varchar(n)
  - sqlserver: nvarchar(max)
    postgresql: text
  - sqlserver: text / ntext
    postgresql: text
    notes: "text/ntext are deprecated in SQL Server; map to PostgreSQL text."

  # Binary
  - sqlserver: binary(n)
    postgresql: bytea
  - sqlserver: varbinary(n)
    postgresql: bytea
  - sqlserver: varbinary(max)
    postgresql: bytea
  - sqlserver: image
    postgresql: bytea
    notes: "image is deprecated; map to bytea."

  # Date / time
  - sqlserver: date
    postgresql: date
  - sqlserver: time(p)
    postgresql: time(p)
  - sqlserver: datetime
    postgresql: timestamp(3)
    notes: "datetime ~3.33ms precision; timestamp(3) is close. Validate rounding."
  - sqlserver: datetime2(p)
    postgresql: timestamp(p)
  - sqlserver: smalldatetime
    postgresql: timestamp(0)
  - sqlserver: datetimeoffset(p)
    postgresql: timestamptz(p)

  # Identifiers / misc
  - sqlserver: uniqueidentifier
    postgresql: uuid
  - sqlserver: rowversion / timestamp
    postgresql: bytea
    notes: "SQL Server 'timestamp'/rowversion is a row-version binary, NOT a datetime — map to bytea or redesign with a trigger; do not map to PG timestamp."
  - sqlserver: xml
    postgresql: xml
  - sqlserver: "sql_variant"
    postgresql: text
    notes: "No equivalent; widen to text or redesign."
  - sqlserver: hierarchyid
    postgresql: "ltree (traversal) — or bytea/varchar (storage-only)"
    notes: >
      No native equivalent. CHOOSE BY USAGE: (1) if any code traverses the tree
      (OrganizationNode.GetAncestor()/GetLevel()/ToString(), IsDescendantOf), map to the
      ltree extension (or a canonical text path like '/1/2/') so ancestor/descendant queries
      become ltree operators (@>, <@) or LIKE, and the traversal procs convert to WITH
      RECURSIVE; (2) if the column is only stored/round-tripped, bytea (opaque) or varchar is
      enough. WARNING: mapping to opaque bytea/varchar BLOCKS any hierarchy-traversal code —
      and AdventureWorks encodes the Employee management chain ONLY in OrganizationNode (no
      ManagerID), so uspGetEmployeeManagers/uspGetManagerEmployees cannot convert unless you
      pick ltree/path. See checks/non-portable-constructs.md.
  - sqlserver: "geography / geometry"
    postgresql: "geometry (PostGIS) — or bytea when PostGIS is unavailable"
    notes: >
      Spatial types/queries need the PostGIS extension. If PostGIS is not enabled
      (e.g. a plain Aurora PostgreSQL without it), map to bytea to round-trip the
      value as opaque bytes (no spatial operations) so the data still migrates and
      reconciles; otherwise use PostGIS geometry/geography. Semantics differ — validate.

# Identifier & schema handling
identifiers:
  sqlserver_quote: brackets ([name]) or double-quotes
  postgresql_quote: double-quotes (folds unquoted to lower_case)
  recommendation: >
    Fold mixed-case SQL Server names to lower_case PostgreSQL identifiers (avoid
    quoted mixed-case which forces quoting everywhere). SQL Server is typically
    case-insensitive (collation-dependent); PostgreSQL is case-sensitive — verify
    queries that rely on case-insensitive matching (use CITEXT or lower()).

# Common gotchas validated in the testing phase
gotchas:
  - "IDENTITY columns -> GENERATED ... AS IDENTITY or sequences; reset after data load."
  - "CLUSTERED indexes have no PostgreSQL equivalent (use CLUSTER command); PK stays a normal index."
  - "GETDATE()->now()/CURRENT_TIMESTAMP, ISNULL->COALESCE, LEN->length, TOP n->LIMIT, + concat->||."
  - "Default collation case-insensitivity differs; PostgreSQL is case-sensitive."
  - "money/datetime rounding differences; rowversion is NOT a timestamp."
  - "T-SQL procedures/funcs -> PL/pgSQL; @@IDENTITY/SCOPE_IDENTITY -> RETURNING/currval."
  - "MERGE supported in modern PG (15+) else INSERT ... ON CONFLICT."
  # --- learned from real AdventureWorks HumanResources + dbo runs ---
  - "CHECK constraints must be IMMUTABLE: a CHECK using getdate()/dateadd() (e.g. age>=18, date<=today) is ILLEGAL in PostgreSQL. Keep the static bounds in the CHECK and enforce the dynamic part with a trigger or in the app."
  - "INSTEAD OF triggers exist only on VIEWs in PostgreSQL. An INSTEAD OF trigger on a TABLE (e.g. make rows undeletable) -> BEFORE trigger that RAISE EXCEPTION (or RETURN NULL to skip)."
  - "Result-set stored procedures (SELECT with no OUTPUT) -> RETURNS TABLE / RETURNS SETOF functions; callers use SELECT * FROM f(...) instead of EXEC. OPTION(MAXRECURSION n) -> a recursionlevel < n guard in the WITH RECURSIVE."
  - "Ambient error functions (ERROR_NUMBER/ERROR_MESSAGE/...) are unreadable from a NESTED proc in PG: pass them as params from the caller's EXCEPTION block via GET STACKED DIAGNOSTICS. TRY/CATCH -> BEGIN..EXCEPTION."
  - "Full-text search (CONTAINS/FREETEXT/CONTAINSTABLE/FREETEXTTABLE) has no equivalent: rebuild with to_tsvector/tsquery + ts_rank and a GIN index. Ranking/inflectional/thesaurus semantics differ — flag, don't claim equivalence."
  - "XML .nodes()/.value()/CROSS APPLY -> xpath() (+ unnest/LATERAL for multi-node sets); pass the namespace array each call. Date text: CONVERT(datetime,REPLACE(v,'Z',''),101) -> replace(v,'Z','')::timestamp."
  - "Equivalence-testing datetime: SQL Server 'datetime' rounds to ~3.33ms ticks; PG timestamp is exact (a -2ms expression yields .997 vs .998). Compare at second/date granularity, or use datetime2, for sub-second values."
  - "Reserved/odd identifiers: a column named [Schema]/[User]/etc. or one containing a space ([Database Version]) must be double-quoted-and-lower-cased in PG."
  - "Run inventory first: it now lists cross-schema dependencies (referenced schemas) — confirm every referenced schema is in migration scope before converting code, or those objects will be runtime-blocked."

```

---

# Engine-specific conversion checks — non-portable constructs (learned from real migrations; review before converting)

## non-portable-constructs

# Non-portable SQL Server → PostgreSQL constructs (field-tested checklist)

Patterns that have **no direct PostgreSQL equivalent** and how to convert them, distilled from
real AdventureWorks runs (Person, Sales, HumanResources, dbo). Each item: the SQL Server
construct, the failure if converted naively, and the recommended conversion. The construction
skill should treat these as "Assisted/Manual" and **flag, never silently approximate**.

## 1. Non-IMMUTABLE CHECK constraints
**SQL Server**: `CHECK ([BirthDate] <= dateadd(year,-18,getdate()))`, `CHECK ([HireDate] <= dateadd(day,1,getdate()))`.
**Failure**: PostgreSQL requires CHECK expressions to be IMMUTABLE; `now()`/`current_date` are not →
`ERROR: functions in check constraint must be marked IMMUTABLE`.
**Convert**: keep the static portion in the CHECK (`CHECK (birthdate >= DATE '1930-01-01')`) and
enforce the dynamic rule (age ≥ 18, "not in the future") with a `BEFORE INSERT/UPDATE` trigger or
in the application. Document the moved rule.

## 2. INSTEAD OF triggers on tables
**SQL Server**: `CREATE TRIGGER dEmployee ON HumanResources.Employee INSTEAD OF DELETE AS ... RAISERROR(...)`.
**Failure**: PostgreSQL allows INSTEAD OF triggers only on **views**, not tables.
**Convert**: a `BEFORE DELETE ... FOR EACH ROW` trigger whose function `RAISE EXCEPTION` (to forbid)
or `RETURN NULL` (to silently skip). Reproduces the net effect (e.g. "employees can't be deleted").

## 3. hierarchyid + tree traversal
**SQL Server**: `OrganizationNode hierarchyid`; procs use `.GetAncestor(1)`, `.GetLevel()`, `.ToString()`.
**Failure**: no hierarchyid type; mapping to opaque `bytea`/`varchar` makes traversal impossible.
**Convert**: if traversed, use **ltree** (or a canonical text path `/1/2/`) so ancestor/descendant
→ `@>`/`<@`/`LIKE` and the procs become `WITH RECURSIVE`. If only stored, `bytea`/`varchar` is fine
**but** then any traversal proc is blocked — flag it. (AdventureWorks Employee encodes the manager
chain ONLY in OrganizationNode; with bytea, `uspGetEmployeeManagers`/`uspGetManagerEmployees` cannot
convert — they must be skipped or the column re-encoded as ltree first.)

## 4. Integrated full-text search
**SQL Server**: `CONTAINS`, `FREETEXT`, `CONTAINSTABLE`, `FREETEXTTABLE` (+ LANGUAGE/THESAURUS/INFLECTIONAL).
**Failure**: no equivalent; the proc won't compile.
**Convert**: PostgreSQL native FTS — `to_tsvector(...) @@ websearch_to_tsquery(...)`, rank with
`ts_rank`, back with a GIN index. Inflectional/thesaurus/language options don't map 1:1 — **flag**
that ranking/match semantics differ; don't assert equivalence in tests.

## 5. Result-set stored procedures
**SQL Server**: a procedure whose body is a bare `SELECT` (e.g. `uspGetBillOfMaterials`).
**Convert**: `CREATE FUNCTION ... RETURNS TABLE (...)` (or `SETOF`); callers switch from
`EXEC p @a,@b` to `SELECT * FROM p(a,b)`. `OPTION (MAXRECURSION n)` → a `recursionlevel < n` guard
inside the `WITH RECURSIVE` CTE. Note the call-convention change for the application.

## 6. Error handling (TRY/CATCH + ambient ERROR_*())
**SQL Server**: `BEGIN TRY ... END TRY BEGIN CATCH ... EXEC dbo.uspLogError END CATCH`, where
`uspLogError` reads `ERROR_NUMBER()/ERROR_MESSAGE()/...` from ambient state.
**Failure**: PostgreSQL cannot read the ambient error from a **nested** routine.
**Convert**: `BEGIN ... EXCEPTION WHEN OTHERS THEN ... END`; in the handler use `GET STACKED
DIAGNOSTICS v := MESSAGE_TEXT` and **pass** the fields into the logging proc (so `usplogerror`
takes parameters). `@@IDENTITY`/`SCOPE_IDENTITY()` → `INSERT ... RETURNING`. `PRINT` → `RAISE NOTICE`.

## 7. XML shredding
**SQL Server**: `col.nodes('/a/b')` + `ref.value('(x)[1]','type')`, `CROSS APPLY`.
**Convert**: `xpath('/ns:a/ns:b/text()', col, ARRAY[ARRAY['ns','<uri>']])` with the namespace passed
every call; for multi-node sets use `CROSS JOIN LATERAL unnest(xpath('/ns:a/ns:b', col, ns)) AS t(node)`
then `xpath('ns:child/text()', t.node, ns)`. Dates stored as text: `replace(v,'Z','')::timestamp`.

## 8. datetime precision in equivalence tests
**SQL Server** `datetime` rounds to ~3.33 ms ticks; PostgreSQL `timestamp` is exact (a `-2 ms`
expression yields `...59.997` vs `...59.998`). Test such values at **second/date** granularity, or
map the column to `datetime2`/`timestamp(p)` and validate the rounding explicitly.

## 9. Reserved / awkward identifiers
Columns named `[Schema]`, `[User]`, `[Object]`, or containing spaces (`[Database Version]`) must be
lower-cased and double-quoted (`"schema"`, `"database version"`). Prefer renaming where the app allows.

## 10. Cross-schema scope (run inventory first)
`dbmig inventory` now reports **cross-schema dependencies**. Before converting code, confirm every
referenced schema is in scope — objects referencing a non-migrated schema (e.g. dbo pricing
functions → Production, the contact TVF → Purchasing) will apply (plpgsql defers name resolution)
but are **runtime-blocked** until that schema is migrated. Flag them in the conversion log.

---

# Playbook topic index — general guidance (open the referenced files under `skills/sqlserver-to-postgresql-playbook/references/` as needed; customer-specific rules above win on conflict)

# ANSI SQL — SQL Server → Aurora PostgreSQL Reference Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Base URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/

Distilled reference notes for the ANSI SQL section of the AWS SQL Server 2019 → Amazon Aurora PostgreSQL Migration Playbook. Each file preserves the playbook's SQL examples and comparison tables.

| Topic | File | Conversion category | SCT automation |
|---|---|---|---|
| Case Sensitivity | [case-sensitivity.md](case-sensitivity.md) | Assisted | SCT lowercases names; DMS transformation rules |
| Constraints | [constraints.md](constraints.md) | Automatic (★★★★★ / ★★★★) | High — action code: Constraints |
| Creating Tables | [creating-tables.md](creating-tables.md) | Assisted (★★★ / ★★★★) | Action code: Creating Tables |
| Common Table Expressions | [common-table-expressions.md](common-table-expressions.md) | Automatic (★★★★★ / ★★★★★) | N/A |
| Data Types | [data-types.md](data-types.md) | Assisted (★★★★ / ★★★★) | Action code: Data Types |
| Derived Tables | [derived-tables.md](derived-tables.md) | Automatic (★★★★★ / ★★★★★) | N/A |
| GROUP BY | [group-by.md](group-by.md) | Automatic (★★★★★ / ★★★★★) | N/A |
| Table JOIN | [table-join.md](table-join.md) | Assisted (★★★★ / ★★★★) | N/A |
| Temporal Tables | [temporal-tables.md](temporal-tables.md) | Manual (★★ / none) | N/A |
| Views | [views.md](views.md) | Assisted (★★★★ / ★★★★) | N/A |
| Window Functions | [window-functions.md](window-functions.md) | Automatic (★★★★★ / ★★★★★) | N/A |

## Key migration takeaways
- **High-effort / manual:** Temporal tables (no Aurora support — rebuild with triggers + custom history table).
- **Watch-outs requiring rewrite:**
  - `SET DEFAULT` referential action, subqueries in check constraints (constraints).
  - `IDENTITY`→`SERIAL`, `ON <File Group>`, table variables, memory-optimized tables, `ROWVERSION` (creating tables).
  - `TINYINT`/`SMALLMONEY`/`BINARY`/`UNIQUEIDENTIFIER`/`HIERARCHYID`/`SQL_VARIANT`/`ROWVERSION` type mappings (data types).
  - `OUTER JOIN` with commas (`*=`/`=*`), `CROSS APPLY`/`OUTER APPLY` → `LATERAL` joins (table join).
  - `WITH CUBE`/`WITH ROLLUP`/`GROUP BY ALL` legacy syntax (group by).
  - Indexed and partitioned views (views).
  - `RECURSIVE` keyword required + integer division casting (CTEs).
- **Mostly seamless:** Derived tables, window functions, basic GROUP BY — syntax largely identical (verify returned data types).


# Configuration — SQL Server → Aurora PostgreSQL

Reference files distilled from the AWS SQL Server→Aurora PostgreSQL Migration Playbook, "Configuration" chapter. Each page compares SQL Server behavior with Aurora PostgreSQL and notes how settings map to Aurora Parameter Groups.

| File | Topic | Conversion category | Key difference |
|---|---|---|---|
| [upgrades.md](upgrades.md) | Configuring Upgrades | N/A | In-place/new-install (SQL Server) vs. managed RDS console/CLI upgrades; no auto major upgrades |
| [session-options.md](session-options.md) | Configuring Session Options | N/A (★★) | `SET` options differ significantly except transaction isolation; `SET ROWCOUNT` for DML → `TOP`/`LIMIT` |
| [database-options.md](database-options.md) | Configuring Database Options | N/A (★) | `ALTER DATABASE … SET` → AWS Database Parameter Group |
| [server-options.md](server-options.md) | Configuring Server Options | N/A (★) | `sp_configure`/`RECONFIGURE` → AWS Cluster & Database Parameter Groups |

## Quick orientation

- **Server options** → Aurora **Cluster Parameter Group** (cluster-wide: `wal_buffers`, `autovacuum`, `client_encoding`) plus **Database Parameter Group** (per-instance: `shared_buffers`, `max_connections`, `effective_cache_size`).
- **Database options** → Aurora **Database Parameter Group**.
- **Session options** → PostgreSQL `SET SESSION` parameters (`client_encoding`, `lock_timeout`, `search_path`, `transaction_isolation`, etc.); inspect via `SELECT * FROM pg_settings WHERE context = 'user';`.
- **Upgrades** → managed via RDS console or `aws rds modify-db-cluster`; major upgrades need `--allow-major-version-upgrade`, a version-compatible parameter group, removal of `reg*` types, extension upgrades, and committed prepared transactions.


# Customer-Specific Knowledge — HIGHEST PRECEDENCE (SQL Server → PostgreSQL)

This folder holds knowledge about **this customer's own environment and application** for the
SQL Server → PostgreSQL (Aurora PostgreSQL) migration — their conventions, datatype
overrides, collation/case-sensitivity expectations, and prior decisions. It is intentionally
empty of vendor content: you fill it in per engagement.

## Precedence rule

Content here **overrides** the general SQL Server playbook references (`../tsql/`,
`../ansi-sql/`, etc.) wherever the two conflict. The conversion tooling injects every active
file in this folder at the **top** of each prompt bundle, labeled highest precedence, ahead
of the general playbook context.

## What belongs here (one Markdown file per topic; all optional)

- `environment.md` — target Aurora PostgreSQL version, available extensions (`citext`,
  `uuid-ossp`, `postgis`, `pg_trgm`), encoding/collation, schema layout.
- `naming-conventions.md` — identifier casing (SQL Server mixed-case → PostgreSQL lower_case),
  object naming rules.
- `datatype-overrides.md` — mappings that override the generic SQL Server → PostgreSQL map
  (e.g. how `bit` flags map, `money` precision, `datetime` precision, `uniqueidentifier`).
- `collation.md` — case-insensitivity requirements (which columns must stay case-insensitive
  → `citext` or `lower()`), accent sensitivity.
- `application-constraints.md` — ORM/app expectations (IDENTITY usage, queries that must not
  change shape, case-insensitive lookups).
- `decisions.md` — agreed redesigns for CLR, Service Broker, linked servers, rowversion,
  hierarchyid, full-text search.
- `forbidden.md` — features/patterns the customer disallows.

## Rules for writing these files

- Be specific and prescriptive — these are instructions applied at conversion time.
- Mark each overriding rule with "Override: …" so intent is unambiguous.
- Keep secrets out — this folder is committed with the repo.

## Status

No customer files are present yet. Add files here at the start of an engagement; until then,
conversion falls back entirely to the general SQL Server playbook references.


# High Availability & Disaster Recovery — Reference Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Section: High availability and disaster recovery

Distilled reference material on backup/restore and HA/DR mapping between
Microsoft SQL Server and Amazon Aurora PostgreSQL.

| File | Topic | Conversion category | SCT automation |
|---|---|---|---|
| [backup-and-restore.md](backup-and-restore.md) | Backup and restore design — recovery models, backup types, restore sequences vs. Aurora continuous backup, PITR, snapshots, cloning | N/A (infra) | N/A — storage-level backup managed by RDS |
| [high-availability-essentials.md](high-availability-essentials.md) | HA/DR solutions — FCI, Always On AGs, Mirroring, Log Shipping vs. Aurora clusters, replicas, endpoints, storage auto-repair | N/A (infra) | N/A |

## Key takeaways

- Aurora PostgreSQL delivers HA and backup as a **managed service**, not via DDL/scripts. There is no datatype/feature rule conversion here — these are infrastructure topics.
- **Backup:** Aurora ≈ SQL Server `FULL` recovery model; continuous incremental backups, 1–35 day point-in-time restore, manual snapshots, copy-on-write cloning. No log/differential/partial backups; automated backups cannot be disabled.
- **HA:** clustering and storage replication are automatic across **three Availability Zones**. FCI/Log Shipping have no equivalent; Always On Availability Groups map to **Aurora Replicas** (up to 15 + primary). Failover is via the **cluster endpoint**; read scale-out via the **reader endpoint**.


# Management — SQL Server → Aurora PostgreSQL Migration Playbook references

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Base URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/

Distilled reference files for the **Management** chapter. Each file follows a fixed structure (topic title, source/URL, conversion category, SCT automation, SQL Server, PostgreSQL, conversion notes).

| File | Topic | Feature compatibility | Primary AWS replacement |
|---|---|---|---|
| [sql-server-agent.md](sql-server-agent.md) | SQL Server Agent and PostgreSQL | N/A | Scheduled AWS Lambda (CloudWatch Events) |
| [alerting.md](alerting.md) | Alerting features | One-star | Amazon RDS event notifications + Amazon SNS |
| [database-mail.md](database-mail.md) | Database mail features | One-star | AWS Lambda + Amazon SES |
| [etl.md](etl.md) | ETL features | None | AWS Glue (+ S3, CloudWatch) |
| [export-import.md](export-import.md) | Export and import features | None | `pg_dump` / `pg_restore` / `COPY` + Amazon S3 |
| [server-logs.md](server-logs.md) | Viewing server logs | Three-star | RDS console / API / CLI / SDKs |
| [maintenance-plans.md](maintenance-plans.md) | Maintenance plans | Three-star | RDS snapshots + `VACUUM`/`ANALYZE`/`REINDEX` |
| [monitoring.md](monitoring.md) | Monitoring features | Three-star | Amazon CloudWatch + Performance Insights |
| [resource-governor.md](resource-governor.md) | Resource governor features | Three-star | Multiple Aurora instances / replicas; parallelism + session controls |
| [linked-servers.md](linked-servers.md) | Linked servers | Three-star | `dblink` / `postgres_fdw` |
| [scripting.md](scripting.md) | Scripting features | None | pgAdmin, AWS CLI, Amazon RDS API/SDKs |

## Cross-cutting themes

- **No in-engine scheduler/agent**: SQL Server Agent jobs, Database Mail, and maintenance scheduling are replaced by scheduled AWS Lambda + Amazon CloudWatch Events, Amazon SES, Amazon SNS, and Amazon RDS automated snapshots.
- **Managed service tooling**: SSMS/PowerShell/SQLCMD administration maps to pgAdmin, `psql`, the AWS Console, AWS CLI, and the Amazon RDS API/SDKs.
- **Observability**: SQL Server Profiler/Extended Events/Query Store and DMVs map to Amazon CloudWatch, Enhanced Monitoring, AWS Performance Insights, and `pg_stat_*` views.
- **Heterogeneous data access**: linked servers map to `dblink` / `postgres_fdw`; SSIS/DTS ETL maps to AWS Glue (convertible via AWS SCT).


# Performance Tuning — SQL Server to Aurora PostgreSQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Section: Performance tuning

Reference files distilled from the AWS Migration Playbook performance-tuning chapter. Each file follows the same structure: conversion category, SQL Server usage (with examples), PostgreSQL usage (with examples), and conversion notes.

| File | Topic | Conversion category | Key difference |
|---|---|---|---|
| [run-plans.md](run-plans.md) | Tuning run plans (`SHOWPLAN`/`STATISTICS XML` ↔ `EXPLAIN`/`EXPLAIN ANALYZE`; Aurora QPM) | Manual (two-star) | Completely different optimizers, operators, and rules; plans not portable |
| [query-hints-and-plan-guides.md](query-hints-and-plan-guides.md) | Query/table/join hints and plan guides ↔ session planning parameters | Manual (two-star) | PostgreSQL has no in-query hints; only coarse session-level planner toggles |
| [managing-statistics.md](managing-statistics.md) | Statistics collection (`CREATE/UPDATE STATISTICS` ↔ `ANALYZE`/autovacuum) | Assisted (three-star) | Similar functionality; syntax/option differences |

## Summary

- **Run plans**: SQL Server uses `SHOWPLAN_*`/`STATISTICS XML` (graphical in SSMS) and built-in automatic tuning; PostgreSQL uses `EXPLAIN`/`EXPLAIN ANALYZE` (text/XML/JSON/YAML), with Aurora Query Plan Management (QPM) for plan stability and adaptability.
- **Hints**: SQL Server has rich statement-level JOIN/table/query hints plus plan guides; PostgreSQL exposes only session-level Query Planning Parameters (`ENABLE_SEQSCAN`, `RANDOM_PAGE_COST`/`SEQ_PAGE_COST`, `ENABLE_NESTLOOP`, etc.) — manual rework required.
- **Statistics**: closest mapping of the three. SQL Server `CREATE/UPDATE STATISTICS` + `AUTO_*` options map to PostgreSQL `ANALYZE` + the `AUTOVACUUM` daemon, tuned via `default_statistics_target` and per-table `autovacuum_*` parameters.


# Physical Storage — SQL Server → Aurora PostgreSQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Reference set distilled from the "Physical storage" chapter.

Reference files comparing SQL Server 2019 physical-storage features against Amazon Aurora PostgreSQL.

| Topic | File | Conversion category | SCT automation |
|---|---|---|---|
| Columnstore index functionality | [columnstore-indexes.md](columnstore-indexes.md) | Manual (no feature compatibility) | N/A |
| Indexed / materialized view functionality | [indexed-and-materialized-views.md](indexed-and-materialized-views.md) | Manual (two-star compatibility) | N/A |
| Partitioning databases | [partitioning.md](partitioning.md) | Assisted (two-star compatibility, three-star automation) | Partitioning |

## Key takeaways

- **Columnstore indexes** have no Aurora PostgreSQL equivalent — manual redesign required (partitioning, BRIN indexes, or a columnar system such as Amazon Redshift for analytics).
- **Indexed views** map to PostgreSQL **materialized views**, but lose automatic refresh and DML support; refresh is manual or trigger-driven and full-only.
- **Partitioning** is broadly supported via declarative partitioning (PostgreSQL 10+), but note PostgreSQL has no `LEFT` boundary, no `EXCHANGE`/`SPLIT`, and no foreign keys referencing partitioned tables.


# Security — SQL Server → Aurora PostgreSQL Reference Index

Distilled reference material from the AWS *SQL Server → Aurora PostgreSQL Migration Playbook*, security section. Each file follows a common structure: source/URL, conversion category, SQL Server usage (with examples), PostgreSQL usage (with examples), and conversion notes.

| Topic | File | Conversion category | Key difference |
|---|---|---|---|
| Data Control Language (GRANT / REVOKE) | [data-control-language.md](data-control-language.md) | Automatic (5★) | Similar syntax; PostgreSQL has no `DENY` |
| Transparent Data Encryption (TDE) | [tde.md](tde.md) | Assisted (4★) | Storage-level encryption managed by Amazon RDS + KMS |
| Column Encryption | [column-encryption.md](column-encryption.md) | Assisted (3★) | `pgcrypto` functions vs SQL Server key hierarchy |
| Users and Roles | [users-and-roles.md](users-and-roles.md) | Assisted (3★) | No users in PostgreSQL — roles only; no Windows Auth |

## Summary

- **DCL** is the most portable: `GRANT`/`REVOKE` map directly. The main gap is SQL Server's `DENY`, which has no PostgreSQL equivalent and must be re-modeled.
- **TDE** changes implementation model entirely — from in-database SQL DDL to RDS storage-level encryption configured via KMS at instance creation.
- **Column encryption** is functionally similar but requires the `pgcrypto` extension and uses `pgp_sym_encrypt`/`pgp_sym_decrypt` instead of SQL Server's `EncryptByKey`/certificate hierarchy.
- **Users and roles** collapse SQL Server's two-tier login/user model into PostgreSQL's single cluster-wide role concept; Windows Authentication has no equivalent.


# Tools & Services — Reference Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook — "Migration tools and services" chapter
> Base URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/

Reference files distilled from the playbook's migration tools & services pages. All entries
are **Conversion category: N/A (tooling)**.

| File | Topic | Summary |
|---|---|---|
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool | Java utility that connects source/target, assesses, and converts schema objects. Step-by-step project setup, assessment report, convert + apply/save-as-SQL. |
| [sct-action-code-index.md](sct-action-code-index.md) | SCT Action Code Index | Master index of SCT automation levels (5★→none) and all action codes per feature (tables, data types, cursors, triggers, indexes, partitioning, etc.). |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service | Managed data migration/replication. Full-load, full-load+CDC, CDC-only. Source/target support, HA failover, KMS/SSL/Secrets Manager security. |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts | Managed RDS on premises (SQL Server, MySQL, PostgreSQL). Not supported with Aurora. KMS-encrypted; backups to Region. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy | Managed connection-pooling proxy for Aurora/RDS PostgreSQL & MySQL. Cuts fail-over time up to 66%; Secrets Manager/IAM integration; no code changes. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | Amazon Aurora Serverless v1 | On-demand autoscaling Aurora config for intermittent/unpredictable workloads. Scaling thresholds, encrypted storage, provisioning steps. |
| [native-tools.md](native-tools.md) | dbmig native-tools note | Informational: dbmig uses Python drivers (pytds for SQL Server, psycopg for PostgreSQL), not sqlcmd/bcp/psql. |

## Key takeaways
- **AWS SCT** converts schema/code objects; **AWS DMS** moves data. They are complementary.
- The **SCT Action Code Index** is the go-to map for what auto-converts vs. needs manual work.
- **RDS Proxy**, **RDS on Outposts**, and **Aurora Serverless v1** are target-side deployment/runtime options, not conversion tools.
- `dbmig` itself relies on Python drivers, independent of these AWS GUI/managed services (see native-tools.md).


# T-SQL Conversion References — SQL Server → Aurora PostgreSQL

Distilled from the AWS *SQL Server to Aurora PostgreSQL Migration Playbook* (T-SQL chapter). Each file follows: Conversion category, SCT automation, SQL Server, PostgreSQL, Conversion notes.

- **service-broker.md** — Native messaging/queuing has no equivalent; re-architect with Amazon SQS + AWS Lambda (+ DB Links). [Manual]
- **cast-and-convert.md** — `CAST` is compatible; rewrite `CONVERT` as `CAST` and date styles as `TO_CHAR`; `::` operator available. [Assisted]
- **common-language-runtime.md** — .NET CLR unsupported; rewrite in PL/pgSQL or PL/Perl (`plperl`). [Manual]
- **collations.md** — Encoding/locale model differs; `UTF16`/`NCHAR`/`NVARCHAR` unsupported; changing encoding needs dump/restore. [Assisted]
- **cursors.md** — Most cursor ops map directly; `@@FETCH_STATUS` unsupported (use `FOUND`); `DEALLOCATE` not needed. [Assisted]
- **date-time-functions.md** — Rich function set; rename functions (`DATEADD`→`INTERVAL`, `DATEDIFF`→`DATE_PART`, `GETUTCDATE`→`at time zone 'utc'`). [Automatic]
- **string-functions.md** — Mostly compatible; rename (`CHARINDEX`→`POSITION`, `STR`→`TO_CHAR`); `PATINDEX` needs a UDF. [Automatic]
- **databases-and-schemas.md** — Same instance/db/schema hierarchy; no `USE` command; no filegroups. [Automatic]
- **dynamic-sql.md** — No `sp_executesql`; use `EXECUTE ... USING` with `format()` (`%I`/`%L`/`%s`); `PREPARE`/`EXECUTE`. [Manual]
- **transactions.md** — Same ANSI levels; nested transactions unsupported (use savepoints); `BEGIN TRAN`→`SET TRANSACTION`. [Assisted]
- **synonyms.md** — No synonyms; emulate with views (tables), wrapper types (UDTs), wrapper functions. [Manual]
- **delete-update-from.md** — `UPDATE ... FROM` supported; `DELETE ... FROM <join>` must be rewritten with a WHERE subquery. [Assisted]
- **stored-procedures.md** — Convert `CREATE PROCEDURE` → `CREATE FUNCTION`; drop `@`; `EXECUTE AS`→`SECURITY DEFINER/INVOKER`; no encryption/recompile/bulk insert. [Assisted]
- **error-handling.md** — `TRY…CATCH`→`BEGIN…EXCEPTION`; `THROW`/`RAISERROR`→`RAISE`; `ERROR_*`→`GET STACKED DIAGNOSTICS`/`SQLSTATE`/`SQLERRM`. [Manual]
- **flow-control.md** — Mostly maps; no `GOTO` (use CASE/nested procs); `WAITFOR`→`pg_sleep`; `BREAK`→`EXIT WHEN`. [Assisted]
- **full-text-search.md** — Full rewrite to `tsvector`/`tsquery` + `@@` and GIN/GiST indexes; CloudSearch for complex needs. [Manual]
- **graph-features.md** — No native graph; use recursive CTEs or relational modeling (or Amazon Neptune). [Manual]
- **json-and-xml.md** — Native `JSONB`/`JSON` and `xml`; operators `->`/`->>`/`?`; no `FOR XML` (use `string_agg`); GIN indexes. [Automatic]
- **merge.md** — No `MERGE` (in target version); rewrite as `INSERT … ON CONFLICT … DO UPDATE`; `OUTPUT`→`RETURNING`. [Assisted]
- **pivot-unpivot.md** — No PIVOT/UNPIVOT; rewrite with `GROUP BY`+`CASE` (pivot) and `CROSS JOIN`/`UNION ALL` (unpivot). [Assisted]
- **triggers.md** — Triggers must call a function; `INSERTED`/`DELETED`→`NEW`/`OLD`; adds BEFORE & row-level; DDL→event triggers. [Assisted]
- **top-fetch.md** — `TOP (n)`/`OFFSET…FETCH`→`LIMIT … OFFSET`; `WITH TIES`/`PERCENT` need workarounds. [Automatic]
- **user-defined-functions.md** — All UDF types → `CREATE FUNCTION` (`RETURNS`/`RETURNS TABLE`/`SETOF`); `APPLY`→`LATERAL`; mark IMMUTABLE/STABLE/VOLATILE. [Assisted]
- **user-defined-types.md** — `CREATE TYPE` in both; scalar UDT→domain/composite; table-valued types→composites/arrays; adds enum/range/array. [Automatic]
- **identity-and-sequences.md** — `IDENTITY`→`GENERATED ... AS IDENTITY`/`SERIAL`; `NEXT VALUE FOR`→`NEXTVAL`; reseed via `SETVAL`; `SCOPE_IDENTITY`→`RETURNING`. [Assisted]


=== TASK — GENERATE EQUIVALENCE TESTS ===
Generate equivalence tests that prove the converted PostgreSQL (Aurora PostgreSQL compatible) view `HUMANRESOURCES.vJobCandidateEducation` behaves the same as the SQL Server source: same input → same return value (functions) or same net effect (procedures). Tests will run on BOTH engines and the results compared.

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


--- SOURCE (VIEW) — HUMANRESOURCES.vJobCandidateEducation ---
CREATE VIEW [HumanResources].[vJobCandidateEducation] 
AS 
SELECT 
    jc.[JobCandidateID] 
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Level)[1]', 'nvarchar(max)') AS [Edu.Level]
    ,CONVERT(datetime, REPLACE([Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.StartDate)[1]', 'nvarchar(20)') ,'Z', ''), 101) AS [Edu.StartDate] 
    ,CONVERT(datetime, REPLACE([Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.EndDate)[1]', 'nvarchar(20)') ,'Z', ''), 101) AS [Edu.EndDate] 
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Degree)[1]', 'nvarchar(50)') AS [Edu.Degree]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Major)[1]', 'nvarchar(50)') AS [Edu.Major]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Minor)[1]', 'nvarchar(50)') AS [Edu.Minor]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.GPA)[1]', 'nvarchar(5)') AS [Edu.GPA]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.GPAScale)[1]', 'nvarchar(5)') AS [Edu.GPAScale]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.School)[1]', 'nvarchar(100)') AS [Edu.School]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.CountryRegion)[1]', 'nvarchar(100)') AS [Edu.Loc.CountryRegion]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.State)[1]', 'nvarchar(100)') AS [Edu.Loc.State]
    ,[Education].ref.value(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
        (Edu.Location/Location/Loc.City)[1]', 'nvarchar(100)') AS [Edu.Loc.City]
FROM [HumanResources].[JobCandidate] jc 
CROSS APPLY jc.[Resume].nodes(N'declare default element namespace "http://schemas.microsoft.com/sqlserver/2004/07/adventure-works/Resume"; 
    /Resume/Education') AS [Education](ref);

--- SAMPLED REAL DATA (use these actual values) ---
### Department  (columns: DepartmentID, Name, GroupName, ModifiedDate)
  1 | Engineering | Research and Development | 2008-04-30 00:00:00
  2 | Tool Design | Research and Development | 2008-04-30 00:00:00
  3 | Sales | Sales and Marketing | 2008-04-30 00:00:00
### Employee  (columns: BusinessEntityID, NationalIDNumber, LoginID, OrganizationNode, OrganizationLevel, JobTitle, BirthDate, MaritalStatus, Gender, HireDate, SalariedFlag, VacationHours, SickLeaveHours, CurrentFlag, rowguid, ModifiedDate)
  1 | 295847284 | adventure-works\ken0 |  |  | Chief Executive Officer | 1969-01-29 | S | M | 2009-01-14 | True | 99 | 69 | True | f01251e5-96a3-448d-981e-0f99d789110d | 2014-06-30 00:00:00
  2 | 245797967 | adventure-works\terri0 | <binary 1 bytes> | 1 | Vice President of Engineering | 1971-08-01 | S | F | 2008-01-31 | True | 1 | 20 | True | 45e8f437-670d-4409-93cb-f9424a40d6ee | 2014-06-30 00:00:00
  3 | 509647174 | adventure-works\roberto0 | <binary 2 bytes> | 2 | Engineering Manager | 1974-11-12 | M | M | 2007-11-11 | True | 2 | 21 | True | 9bbbfb2c-efbb-4217-9ab7-f97689328841 | 2014-06-30 00:00:00
### EmployeeDepartmentHistory  (columns: BusinessEntityID, DepartmentID, ShiftID, StartDate, EndDate, ModifiedDate)
  1 | 16 | 1 | 2009-01-14 |  | 2009-01-13 00:00:00
  2 | 1 | 1 | 2008-01-31 |  | 2008-01-30 00:00:00
  3 | 1 | 1 | 2007-11-11 |  | 2007-11-10 00:00:00
### EmployeePayHistory  (columns: BusinessEntityID, RateChangeDate, Rate, PayFrequency, ModifiedDate)
  1 | 2009-01-14 00:00:00 | 125.5 | 2 | 2014-06-30 00:00:00
  2 | 2008-01-31 00:00:00 | 63.4615 | 2 | 2014-06-30 00:00:00
  3 | 2007-11-11 00:00:00 | 43.2692 | 2 | 2014-06-30 00:00:00
### JobCandidate  (columns: JobCandidateID, BusinessEntityID, Resume, ModifiedDate)
  1 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
  2 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
  3 |  | <ns:Resume xmlns:ns="http://schemas.microsoft.com/sqlserver/2004/07/adventure-wo… | 2007-06-23 00:00:00
### Shift  (columns: ShiftID, Name, StartTime, EndTime, ModifiedDate)
  1 | Day | 07:00:00 | 15:00:00 | 2008-04-30 00:00:00
  2 | Evening | 15:00:00 | 23:00:00 | 2008-04-30 00:00:00
  3 | Night | 23:00:00 | 07:00:00 | 2008-04-30 00:00:00
