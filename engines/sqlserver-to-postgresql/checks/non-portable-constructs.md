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

## 11. Spatial (geography/geometry) + moving hierarchyid/geography data
`geography`/`geometry` and `hierarchyid` come back from the driver as **opaque binary**, so a generic
COPY into a target `text` column fails or stores garbage. Convert at **read time** with the source
method: `hierarchyid` → `col.ToString()` (`/1/2/` path), `geography`/`geometry` → `col.STAsText()`
(WKT). `dbmig migrate-data` applies these conversions automatically for those types; if you load such a
table by hand, use the same expressions. Target mapping: `geography` → `text` (WKT) or PostGIS
`geography` (`CREATE EXTENSION postgis`); `hierarchyid` → `text` (or `ltree`). A computed
`OrganizationLevel` (from `OrganizationNode.GetLevel()`) → a plain `smallint` loaded from the source
value (or a generated column).

## 12. Procedures that manage their own transactions are not net-effect testable
A procedure containing `BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK` cannot be validated by `run-tests`
(which wraps each case in a transaction and rolls back): an internal `COMMIT` persists to the **source**,
and an internal `ROLLBACK` unbalances the harness transaction (SQL Server **error 266**, "Transaction
count … mismatching number of BEGIN and COMMIT"). `dbmig gen-tests` flags these (`test_mode: manual`).
Write a **non-destructive** case (target a non-existent key so the mutation matches zero rows on both
engines) or leave `cases: []` and note it. Also: passing a `hierarchyid` argument to `EXEC` needs a
declared variable — `DECLARE @o hierarchyid = hierarchyid::Parse(N'/2/'); EXEC … @node=@o` — an inline
`CAST(...)` is rejected.
