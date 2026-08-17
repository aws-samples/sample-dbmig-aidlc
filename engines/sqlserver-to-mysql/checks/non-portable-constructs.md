# Non-portable SQL Server → MySQL constructs (field-tested checklist)

Patterns with no direct Aurora MySQL equivalent and how to convert them, distilled from a real
AdventureWorks `Person` + `Sales` → Aurora MySQL 8.0 run (32 tables, 22 FKs, 4 of 9 views).
Flag, don't silently approximate.

## 1. IDENTITY / AUTO_INCREMENT placement
`int IDENTITY(1,1)` → `int AUTO_INCREMENT`. MySQL requires the AUTO_INCREMENT column to be the
**leading column of some key**. When IDENTITY is the *second* PK column (e.g.
`EmailAddress(BusinessEntityID, EmailAddressID)`, `SalesOrderDetail(SalesOrderID,
SalesOrderDetailID)`), add an extra `KEY(identitycol)`. `migrate-data` reseeds AUTO_INCREMENT
after load.

## 2. Types
- `uniqueidentifier` → `char(36)`; `NEWID()` default → `DEFAULT (UUID())` (MySQL 8 expression
  default needs parentheses). `binary(16)` + `UUID_TO_BIN` is a denser alternative.
- `bit` → `tinyint(1)`; `DEFAULT ((0))` → `DEFAULT 0`.
- `money` → `decimal(19,4)`, `smallmoney` → `decimal(10,4)`, `numeric(p,s)` → `decimal(p,s)`.
- `datetime` → `datetime(3)`; `GETDATE()` default → `DEFAULT CURRENT_TIMESTAMP(3)` (MySQL 8
  allows multiple such columns per table). `datetime2(p)` → `datetime(LEAST(p,6))`.
- `tinyint` is **signed** in MySQL but 0-255 in SQL Server → use `tinyint UNSIGNED`.
- `xml` → `longtext` (or JSON); `geography`/`geometry` → `longblob` (opaque) unless using MySQL
  spatial; `rowversion`/`timestamp` is a binary row-version, NOT a datetime → `binary(8)`.

## 3. Computed / persisted columns
SQL Server computed columns (e.g. `SalesOrderHeader.SalesOrderNumber`/`TotalDue`,
`SalesOrderDetail.LineTotal`, `Customer.AccountNumber`) → migrate as **STORED plain columns**
(load the computed value), or a MySQL `GENERATED ... STORED` column when the expression is
portable (no UDF/system-function dependency). Loading the value keeps the target identical to
the source snapshot.

## 4. Reserved-word / mixed-case identifiers
Fold to lower_case; backtick-quote reserved words (`[Group]` → `` `group` ``). SQL Server is
usually case-insensitive; on Linux MySQL table names are case-sensitive — pick a collation
(e.g. `utf8mb4_0900_ai_ci`) and casing convention to match app expectations.

## 5. Namespaced-XML views (HARD BLOCK)
MySQL's `ExtractValue`/`UpdateXML` use a limited XPath and **do NOT support XML namespaces**.
SQL Server views that shred namespaced XML with `.value()`/`.nodes()` (AdventureWorks
`vPersonDemographics`, `vStoreWithDemographics`, `vAdditionalContactInfo` over the
IndividualSurvey/StoreSurvey namespaces) **cannot** be reproduced — flag/skip. (PostgreSQL can,
via `xpath()` with a namespace array; MySQL cannot.) If needed, re-model the XML as JSON and use
MySQL JSON functions.

## 6. Schema = database; cross-database refs
A SQL Server schema maps to a MySQL **database** (`Person`→`person`, `Sales`→`sales`). Qualify
objects `db.table`; cross-database joins, views, and foreign keys all work with qualified names.
The deferred FK + multi-statement apply (see the framework's MULTI_STATEMENTS support) applies a
table's several `ALTER ... ADD FOREIGN KEY` statements together.

**Do NOT qualify DDL with the connection's `database:` value** — the target database is derived
from the **source schema name** (lower-cased); the connection's database is only the login
default. Wrongly-qualified DDL applies cleanly and only fails at the data load. The conversion
prompt states the exact target database, and `apply-schema` cross-checks the catalog afterwards.

## 7. T-SQL programmable objects
`IDENTITY`→`AUTO_INCREMENT`; `SCOPE_IDENTITY()`/`@@IDENTITY`→`LAST_INSERT_ID()`;
`GETDATE()`→`NOW()`; `ISNULL`→`IFNULL`/`COALESCE`; `LEN`→`CHAR_LENGTH`; `TOP n`→`LIMIT n`;
`+` string concat→`CONCAT()`; `MERGE`→`INSERT ... ON DUPLICATE KEY UPDATE`; `TRY/CATCH`→
`DECLARE ... HANDLER`; `RAISERROR`/`THROW`→`SIGNAL SQLSTATE`. CLR, Service Broker, linked
servers, integrated full-text search, and columnstore have no equivalent — redesign or use AWS
services. Triggers must be created in the table's database (qualify the trigger name).

## 8. FKs to non-migrated schemas
In a partial migration, foreign keys to out-of-scope schemas (e.g.
`SalesOrderHeader → Purchasing.ShipMethod`, `SalesPerson → HumanResources.Employee`,
`* → Production.Product`) are **omitted and flagged**, not enforced. Run `inventory` first — it
reports cross-schema dependencies so you can confirm scope before converting.

## 9. Partitioning: SQL Server cannot reject an out-of-range row — MySQL can
SQL Server's **partition function + partition scheme** pair has no MySQL equivalent; both collapse
into an inline `PARTITION BY RANGE (col) (PARTITION ... VALUES LESS THAN ...)` clause, and the
filegroup list is dropped.

- **N boundaries always yield N+1 partitions in SQL Server**, so the source table has a catch-all
  at each end and can never reject a row for being out of range. Converting naively therefore
  **introduces a runtime failure the source did not have**:
  `ERROR 1526 (HY000): Table has no partition for value`. Always end with
  `PARTITION pmax VALUES LESS THAN (MAXVALUE)`. MySQL has **no `DEFAULT` partition** (that is
  PostgreSQL), and `LIST` partitioning has no catch-all at all — every value must be enumerated.
- **`RANGE LEFT` (SQL Server default) vs `RANGE RIGHT` decides which partition owns the boundary
  value.** MySQL `VALUES LESS THAN (v)` is exclusive of `v`, matching **`RANGE RIGHT`**. For
  `RANGE LEFT`, shift the bound by one increment or rows land in the neighbouring partition —
  silent misplacement, no error.
- **Every unique key, including the PRIMARY KEY, must contain all partitioning columns**
  (`ERROR 1503`). SQL Server allows a non-aligned unique index; MySQL does not. Adding the column
  **weakens uniqueness** to per-partition — mark it and get sign-off.
- **Partitioned InnoDB tables cannot participate in foreign keys at either end** (`ERROR 1506`).
  For a heavily-referenced fact table this often decides the design: drop the partitioning, or drop
  the FKs and enforce integrity in the application. Never discard a constraint silently — and note
  this pair already omits FKs to non-migrated schemas (item 8), so keep the two cases distinct in
  the conversion log.
- `SWITCH`/`MERGE`/`SPLIT RANGE` → `ALTER TABLE ... EXCHANGE PARTITION` covers some `SWITCH` cases;
  `$PARTITION.pf()` has no equivalent.

## 10. Views: MySQL coerces types too — which is more dangerous, not less
Views are converted in the **stored-code pass** and applied **after functions**, since a view that
calls a function cannot be created first.

- Both SQL Server and MySQL coerce silently across types, so a mismatched join **will not error**
  on either side — but they use **different rules**: MySQL converts a non-numeric string to `0`
  rather than raising. A join that "worked" in SQL Server can therefore return *different rows* in
  MySQL with no diagnostic. Add explicit `CAST`s where the source relied on coercion and treat it
  as a data-quality finding; this is exactly the class of difference the equivalence tests exist
  to catch, so include such joins in a query-parity case.
- MySQL views have real restrictions: **no subquery in the `FROM` clause of a view** in older
  versions, `WITH` (CTE) needs 8.0+, and a view cannot reference a temporary table or a variable.
  `CROSS APPLY`/`OUTER APPLY` → `JOIN LATERAL` (MySQL 8.0.14+) or a rewritten join.
- `TOP n` → `LIMIT n`; `ISNULL` → `IFNULL`; `+` concat → `CONCAT()`;
  `WITH SCHEMABINDING` → drop. `WITH CHECK OPTION` is supported.
- MySQL has no `INSTEAD OF` triggers, so a non-updatable view that SQL Server made writable that
  way must be handled in the application.
- Keep the explicit column list, lower-cased consistently with the body.

## 11. Table types and table-valued parameters
`CREATE TYPE x AS TABLE (...)` passed as a `READONLY` TVP has no MySQL equivalent, and MySQL has
**no arrays and no composite types** to fall back on (unlike PostgreSQL). Options:

1. **A `JSON` parameter** expanded with `JSON_TABLE(...)` (MySQL 8.0+) — the closest to set-based.
2. **A `TEMPORARY TABLE`** the caller populates before `CALL` — most faithful to the T-SQL idiom.

Both change the **caller contract**: any client binding a TVP must be rewritten. Flag every
occurrence. A `MERGE` driven by a TVP is affected twice, since `MERGE` itself becomes
`INSERT ... ON DUPLICATE KEY UPDATE` (item 7).

## 12. CHECK constraints calling getdate() are rejected — SEMANTIC CHANGE
MySQL 8 CHECK constraints cannot reference non-deterministic functions
(`ERROR 3814: An expression of a check constraint ... contains disallowed function: now`).
SQL Server CHECKs like `[BirthDate] <= dateadd(year,(-18),getdate())` therefore have no
direct port (PostgreSQL, by contrast, accepts `now()` in CHECK). Options:
1. Keep only the deterministic part of the constraint and DROP the now()-relative bound —
   mark it inline and record a semantic change for sign-off (the rule is no longer enforced
   by the database); enforce it in the application or a BEFORE trigger if load-bearing.
2. Rewrite as a `BEFORE INSERT/UPDATE` trigger that SIGNALs on violation — preserves
   enforcement at the cost of trigger machinery.
Never drop the whole constraint silently: static bounds (e.g. `>= '1930-01-01'`) still port.
