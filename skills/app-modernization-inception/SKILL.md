---
name: app-modernization-inception
description: >
  INCEPTION phase (assessment) of the optional application-modernization module: scan an
  application and classify every site impacted by a database migration — embedded SQL,
  datasource/ORM configuration, entity mappings, stored-routine call sites, error-code handling
  and result-set typing. Engine-agnostic; reads the active pair's rules from engines/<pair>/app/.
  Invoked by app-modernization-orchestrator, which turns this assessment into the gated change
  plan; read-only, edits nothing. Produces
  migrations/<project>/05-application/01-assessment/inventory.md.
---

# Application Modernization — Inception (assessment)

Find everything the migration affects, classify it, and be honest about what cannot be resolved
statically. **This skill reads and reports only — it never edits.**

Inputs: `00-intake/app-intake.md` (stack, scope), `01-assessment/app-contract.md`
(what the migration changed), `engines/<pair>/app/app-config.yaml` and `app-sql-rules.md`,
and — **as the highest-precedence context** — every `*.md` in
`engines/<pair>/app/customer-specific/` (the customer's own app conventions/overrides;
`_index.md` is the guide). Where customer-specific rules conflict with the generic app
rules, the customer file wins.

## Step 0 — Run the deterministic pre-scan FIRST (do not walk the tree by hand)

```bash
./dbmig app-scan --app-dir <APP_DIR> --project <project> [--target-schema <schema>]
```

It walks the whole application once (build output, dependencies, VCS and vendored front-end
assets excluded), reconstructs string literals per language (Java/Kotlin concatenation and
text blocks, C# verbatim/interpolated, Python triple/implicit, JS/TS templates), MyBatis /
Hibernate XML, and writes `05-application/01-assessment/app-scan.md` (compact) +
`app-scan.yaml` (full). It detects the frameworks in use (JPA/Hibernate, Spring JDBC, MyBatis,
jOOQ, EF Core, EF6, NHibernate, Dapper, ADO.NET, SQLAlchemy, Django, raw DB-API drivers,
Sequelize, TypeORM, Knex, Prisma, Node drivers), extracts ORM mappings (JPA annotations,
EF Core data annotations + fluent `OnModelCreating` + inherited base-class properties + `DbSet`
names, SQLAlchemy, Django, TypeORM, Sequelize, Prisma), and — with a target connection —
**cross-checks every mapped field against the live migrated column type** (C1 below),
including EF Core's quoted-identifier case trap.

**Read `app-scan.md`, then open only its *flagged files*.** On a large code base (1,000+ files)
this is the difference between reading a few dozen files and reading all of them. Use the
categories below to *classify and verify* what the scan found — not to re-discover it. The scan
is a floor, not a ceiling: it cannot see SQL built from configuration or the database, LINQ /
criteria-API queries, or dynamic identifiers, so still apply judgment to the flagged files and
their callers, and state the coverage caveat.

For very large code bases, fan out by flagged-file slices (sub-agents), each returning its
per-site classification rows; merge them into one inventory.

## Scope discipline

Search only the in-scope source directories. **Always exclude** build output and dependencies:
`target/`, `build/`, `bin/`, `obj/`, `dist/`, `out/`, `node_modules/`, `.git/`, `vendor/`,
`__pycache__/`, `*.class`, `*.jar`, `*.dll`, minified assets.

A hit inside build output means the artifact is stale, not that there is a site to convert.
Report such files separately as **stale build artifacts**, and note any `.bak`/`.orig` leftovers
from previous ad-hoc conversions — they are not conversion targets.

## Categories to inventory

### A. Connectivity & framework configuration
Datasource URL, driver class, ORM dialect, connection pool, schema/search-path selection.
Typical locations: `application.properties|yml`, `appsettings*.json`, `web.config`,
`persistence.xml`, `hibernate.cfg.xml`, `*.env`, Helm/Terraform values, Dockerfiles, CI config.
Record the file, the key, and the current value — **redact passwords** (`password=***`).

**Also scan CODE that parses or builds connection URLs** — grep for `jdbc:`, the driver class
name, and URL-string surgery (`split`, `substring`, regex) on a datasource URL. In two real runs
this was missed by config-only scanning: display/diagnostic classes split the URL on Oracle's
`@//` token, and their fallback echoed the raw URL — a credential-leak path once query parameters
carry secrets. URL *format* assumptions are code sites, not config sites.

### B. Embedded SQL
Classify each site by **tier**, because tier determines whether it can be converted safely:

| Tier | What | Conversion approach |
|---|---|---|
| 1 | Externalised SQL (`*.sql`, MyBatis/iBatis mappers, `.xml`) | convert directly |
| 2 | Complete statement in a constant, annotation or literal (`@Query`, `const string`) | convert directly |
| 3 | Assembled at runtime (`StringBuilder`, conditional fragments, dynamic `WHERE`) | **reconstruct the full statement first**, then convert; never rewrite a fragment in isolation |
| 4 | Generated by a builder/ORM criteria API, or fetched from the DB/config | usually no SQL text to edit — fix the generator, the dialect, or flag for redesign |

For each site record: file, line range, tier, whether the statement is complete, the constructs
found, and mechanical vs behavioural.

**Reconstruct multi-line statements BEFORE pattern-matching** (`dbmig app-scan` already does
this for the languages it covers). A per-line grep misses SQL split
across concatenated string literals — in a real run the first `CONTAINS` search missed
`BookRepository.fullTextSearchBooks` because the statement spanned `"SELECT … " +` /
`"WHERE CONTAINS(…" +` lines. For every file with SQL-looking literals: join adjacent
concatenated literals (`"…" + "…"`, Java text blocks `"""…"""`, C# `@"…"`/`$"…"`, Kotlin
`trimIndent()`, Python implicit concatenation / triple quotes, `StringBuilder.append` chains)
into one logical statement per method, *then* search the joined text. Do not assume `rg` is
installed; a portable joiner (verified on a Spring `@Query` split over three `" +` lines):
```python
import re, pathlib, sys
for p in pathlib.Path(sys.argv[1]).rglob("*.java"):          # or *.cs, *.kt, *.py …
    s = p.read_text(errors="ignore")
    j = re.sub(r'"\s*\+\s*\n\s*"', "", s)                    # join "…" +\n "…"
    for m in re.finditer(r'"([^"]*\b(?:CONTAINS|SCORE|ROWNUM|NVL|DECODE|SYSDATE)\b[^"]*)"', j):
        print(f"{p}:{j[:m.start()].count(chr(10)) + 1}: {m.group(1)}")
```
(extend the keyword list from the pair's rules; line numbers are the statement's first line).
Or read the whole method. Record the site's line range as the full span, not one matching line.

Search terms come from the pair's `app-sql-rules.md`. For an Oracle source, at minimum:
`SYSDATE`, `SYSTIMESTAMP`, `NVL`, `NVL2`, `DECODE`, `DUAL`, `ROWNUM`, `CONNECT BY`, `(+)`,
`MINUS`, `LISTAGG`, `TO_DATE`, `TO_CHAR`, `TRUNC`, `ADD_MONTHS`, `MONTHS_BETWEEN`, `NEXTVAL`,
`CONTAINS(`, `CATSEARCH`, `SCORE(`, `/*+`, `FETCH FIRST`, `REGEXP_`. For SQL Server:
`GETDATE`, `ISNULL`, `TOP `, `IDENTITY`, `@@IDENTITY`, `SCOPE_IDENTITY`, `LEN(`, `MERGE`,
`CROSS APPLY`, `OUTER APPLY`, `NOLOCK`, `+` string concat, `DATEADD`, `DATEDIFF`, `CONVERT(`.

### C. ORM entity mappings
Per stack, the same class of site:
- **JPA/Hibernate**: `@Table`/`@Column`/`@Entity` names — especially **quoted** identifiers,
  which pin the old case; `@SequenceGenerator`/`@GeneratedValue` strategies, type converters,
  `@Lob`, `@Enumerated`, `ddl-auto`/schema-generation settings.
- **EF Core**: `ToTable`/`HasColumnName`/`DbSet` naming conventions, `OnModelCreating`
  configuration, value converters, `HasDefaultValueSql` (dialect-specific SQL inside the model!),
  owned types, and any `Database.EnsureCreated`/migration invocation at startup.
- **MyBatis/Dapper/SQLAlchemy/Sequelize**: mapping files or attribute conventions equivalent
  to the above.

**Cross-check mapped names against the SOURCE catalog.** For each explicit table mapping
(JPA `@Table(name=…)`, EF `ToTable("…")`/`DbSet` conventions), confirm the named table actually
exists in the source schema. Real apps drift: one mapped `Order` → `ToTable("Orders")` while the
source table was `Order` — the migration surfaces such drift as a hard failure, so classify it at
inventory time (conform to the migrated name + flag), not during build fixing.

For **EF Core** apps specifically, record that the model emits *quoted PascalCase* identifiers:
a pure-LINQ app with zero SQL text still breaks against a case-folded schema, so the change plan
must include the `OnModelCreating` lower-case fold (see the pair's app-sql-rules).

#### C1. Entity field type ↔ migrated column type cross-check (REQUIRED for ORM apps)

**This is the single highest-value inventory step — `dbmig app-scan` does it mechanically**
(its *C1* table lists each field with the migrated type and the ORM-specific fix; *mapping
issues* lists tables/columns missing in the target and quoted-identifier case mismatches).
Verify its rows and add anything it could not see (custom converters, `@Convert`, value
objects). The manual procedure below is the fallback when no target is reachable or for a
stack the scanner does not parse.

In a real run, three ORM mismatches passed
a clean compile *and* the static scan and were only found when the app booted with
`ddl-auto=validate` — one boot failure per table. All three were the same class: *a mapped
field on a column whose type the DB migration changed*. Do the cross-check up front so each
becomes a planned change-plan row instead of a boot-time surprise:

1. **Get the migrated column types** — preferably from the **live target catalog** (read-only),
   else from the DB migration's `02-construction/conversion-log.md` / converted DDL:
   ```sql
   SELECT table_name, column_name, data_type, udt_name, character_maximum_length,
          numeric_precision, numeric_scale
   FROM information_schema.columns WHERE table_schema = '<target_schema>'
   ORDER BY table_name, ordinal_position;
   ```
2. **Get the source types** for the same columns (source catalog or `01-assessment/inventory`),
   so each row shows *what changed*.
3. **Map every entity field to its column** — `@Table`/`@Column` names or the naming strategy
   (Spring Boot's default snake_case), EF `HasColumnName`/conventions — and record the Java/C#
   type plus any `@Lob`, `@Temporal`, `@Convert`, `@JdbcTypeCode`, `columnDefinition`.
4. **Flag every field on a retyped column.** The pair's `app-config.yaml`
   `orm_type_obligations` lists the ones that are *always* an obligation (for Oracle →
   PostgreSQL: `NUMBER(1)→smallint` + `Boolean`, `DATE→timestamp` + `LocalDate`,
   `BLOB→bytea` + `@Lob byte[]`, `CLOB→text` + `@Lob String`, `NUMBER(10)→bigint` + `Integer`).
   Also flag any field whose Java/C# type does not match the target column family at all.
5. Output a **type cross-check table** in the inventory: entity.field → column → source type →
   target type → Java type/annotations → obligation (fix recipe from `app-sql-rules.md` §5a)
   or `OK`. Every non-OK row becomes a change-plan row. State the count of fields checked so a
   reviewer can see the check was exhaustive, not sampled.

If neither the live catalog nor the conversion log is available, say so and mark the whole
category **undecidable** — do not guess column types from the entity.

#### C2. Existence check against the SOURCE catalog — pre-existing vs migration-caused

For **every** table referenced in embedded SQL / entity mappings and **every** stored routine
called from the app, confirm it exists in the **source** schema (read-only, e.g. Oracle
`ALL_OBJECTS` / `ALL_TAB_COLUMNS`, SQL Server `sys.objects`), and for embedded SQL also check
the referenced **columns**. Pre-classify each site:

- **`migration-impacted`** — exists in the source; the migration changed its name/type/shape.
  Convert it.
- **`pre-existing-broken`** — does **not** exist in the source (e.g. an app call to
  `get_customer_history` that was never created; demo classes selecting `b.name`/`SALES`
  columns/tables absent from the schema). The migration did not break it. Like-for-like means:
  do a mechanical dialect conversion at most, **flag it loudly** as pre-existing, and ask the
  user (ambiguity gate) — never "fix" it by inventing the missing object.
- **`dead-code`** — unreachable/unused (no callers, demo/sample packages) — list separately.

Cite the catalog query result for each `pre-existing-broken` verdict; it is what makes the call
defensible.

### D. Stored-routine call sites
`CallableStatement`, `{ call … }`, `@Procedure`, `EntityManager.createStoredProcedureQuery`,
Dapper `CommandType.StoredProcedure`, `EXEC`. For each: the routine name as called, whether the
migration renamed it (package flattening), whether it became a function rather than a procedure,
`OUT`/ref-cursor parameters, and whether the routine lost an internal `COMMIT` (making the caller
responsible for the transaction).

### E. Error handling
`getErrorCode()`, `ORA-` string matching, `SQLException` subclasses, `@SQLExceptionTranslator`,
.NET `OracleException.Number`, SQL Server `SqlException.Number`. Each must move to the target's
error identity (SQLSTATE for PostgreSQL, error numbers for MySQL) using the mapping recorded in
the migration's conversion log.

### F. Result-set typing & column access
Same class of site per stack:
- **JDBC**: `rs.getInt("…")` on a `COUNT(*)` (now `bigint` → `getLong`), column lookups by
  the source engine's case, `getObject` casts, `getDate` vs `getTimestamp`.
- **ADO.NET/Dapper**: `reader["Col"]` / `reader.GetInt32(...)` on counts (→ `GetInt64`),
  ordinal-vs-name access, `DataTable` typing, Dapper materialization of changed types
  (`bit`→`boolean` binds `true/false`, not `0/1`).
- All stacks: boolean-vs-numeric flag reads and date/time precision reads.

### G. Schema-qualified references in app code
Hard-coded `SCHEMA.TABLE` prefixes, and any `search_path`/default-schema assumption.

### H. Build dependencies
The source database driver (and any Oracle/SQL-Server-only library) in `pom.xml`,
`*.csproj`, `requirements.txt`, `package.json`. Note whether the target driver is already
present — a half-finished earlier attempt is common.

## Output — `01-assessment/inventory.md`

1. **Summary table**: category → site count → files touched → mechanical / behavioural / blocked.
2. **Per-category detail**, each site with file, line, tier, current code and the construct found.
3. **Type cross-check table** (C1) — every mapped field checked, with its obligation or `OK`.
4. **Behavioural list** — sites that can change results silently, called out separately.
5. **Pre-existing-broken / dead-code** (C2) — with the source-catalog evidence for each.
6. **Blocked / undecidable** — Tier 3/4 statements that cannot be reconstructed statically,
   routines whose target shape is unknown, dynamic SQL from config or the database.
7. **Not-a-target** — stale build artifacts, `.bak` leftovers, vendored code.
8. **Carry-forwards from the DB migration** — `decision_items` (e.g. `fulltext_redesign` →
   the CONTAINS/SCORE sites), and `LOW_COVERAGE` objects from the equivalence report (app
   paths over those tables are untested on real data too).
9. **Coverage caveat**, stated plainly: static scanning cannot find SQL assembled from
   configuration, generated at runtime, or stored in the database. If the app has integration
   tests or a query log, say so — running them is the reliable way to surface the remainder.
   For runnable ORM apps, the Validation phase's boot against the target is the proof.

Do not propose fixes here; that is the change plan's job. Inventory establishes *what exists*.
