# Query Hints and Plan Guides

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tuning.queryplanning.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** N/A

SQL Server hints force overrides of the query processor's automatic choices for DML/DQL statements. PostgreSQL does not support database hints in queries; it offers only a very limited set of influence via session-level Query Planning Parameters.

## SQL Server

Hints are instructions that override the query processor's automatic choices. Despite the name, a hint *forces* an override of any other run-plan choice.

**JOIN hints** — `LOOP`, `HASH`, `MERGE`, `REMOTE` force a specific physical join algorithm; `REMOTE` runs a join with a remote table on the local server. Example: `… Table1 INNER LOOP JOIN Table2 ON …`.

**Table hints** — force a locking strategy or access method for a table clause for the duration of the statement. Common: `INDEX = <Index value>`, `FORCESEEK`, `NOLOCK`, `TABLOCKX`.

**Query hints** — affect the entire set of query operators. Common: `OPTIMIZE FOR`, `RECOMPILE`, `FORCE ORDER`, `FAST <rows>`. Specified after the query in the `OPTION` clause.

Query hint syntax:

```sql
SELECT <statement>
OPTION
(
{{HASH|ORDER} GROUP
|{CONCAT |HASH|MERGE} UNION
|{LOOP|MERGE|HASH} JOIN
|EXPAND VIEWS
|FAST <Rows>
|FORCE ORDER
|{FORCE|DISABLE} EXTERNALPUSHDOWN
|IGNORE_NONCLUSTERED_COLUMNSTORE_INDEX
|KEEP PLAN
|KEEPFIXED PLAN
|MAX_GRANT_PERCENT = <Percent>
|MIN_GRANT_PERCENT = <Percent>
|MAXDOP <Number of Processors>
|MAXRECURSION <Number>
|NO_PERFORMANCE_SPOOL
|OPTIMIZE FOR (@<Variable> {UNKNOWN|= <Value>}[,...])
|OPTIMIZE FOR UNKNOWN
|PARAMETERIZATION {SIMPLE|FORCED}
|RECOMPILE
|ROBUST PLAN
|USE HINT ('<Hint>' [,...])
|USE PLAN N'<XML Plan>'
|TABLE HINT (<Object Name> [,<Table Hint>[[,...]])
});
```

**Plan guides** apply hints (or a full fixed XML plan) to a query *without editing its text* — useful for ad-hoc queries or third-party software you cannot modify. At run time SQL Server matches the query text and attaches the `OPTION` hints or assigns the stored plan. Three types:

- **Object plan guides** — target statements inside a code object (stored procedure, function, trigger); not applied if the same statement appears elsewhere.
- **SQL plan guides** — match general ad-hoc statements not in a code object; applied to any instance regardless of originating client.
- **Template plan guides** — abstract statement templates differing only in parameter values; override the `PARAMETERIZATION` database option for a query family.

Create-plan-guide syntax:

```sql
EXECUTE sp_create_plan_guide @name = '<Plan Guide Name>'
  ,@stmt = '<Statement>'
  ,@type = '<OBJECT|SQL|TEMPLATE>'
  ,@module_or_batch = 'Object Name>'|'<Batch Text>'| NULL
  ,@params = '<Parameter List>'|NULL }
  ,@hints = 'OPTION(<Query Hints>'|'<XML Plan>'|NULL;
```

Limit parallelism for a report query via a plan guide:

```sql
EXEC sp_create_plan_guide
  @name = N'SalesReportPlanGuideMAXDOP',
  @stmt = N'SELECT *
    FROM dbo.fn_SalesReport(GETDATE())
  @type = N'SQL',
  @module_or_batch = NULL,
  @params = NULL,
  @hints = N'OPTION (MAXDOP 1)';
```

Table and query hints together:

```sql
SELECT *
FROM MyTable1 AS T1
  WITH (FORCESCAN)
  INNER LOOP JOIN
  MyTable2 AS T2
  WITH (TABLOCK, HOLDLOCK)
  ON T1.Col1 = T2.Col1
WHERE T1.Date BETWEEN DATEADD(DAY, -7, GETDATE()) AND GETDATE()
```

## PostgreSQL

PostgreSQL does not support in-query database hints and you cannot influence plan generation from within SQL. Instead, session parameters (Query Planning Parameters) influence the optimizer at the session level.

Force indexes instead of full table scans (disable sequential scans):

```sql
SET ENABLE_SEQSCAN=FALSE;
```

Adjust page-cost estimates. Lowering `RANDOM_PAGE_COST` relative to `SEQ_PAGE_COST` makes index scans more attractive; raising it makes them more expensive:

```sql
SET SEQ_PAGE_COST to 4;
SET RANDOM_PAGE_COST to 1;
```

Discourage nested-loop joins (cannot be fully disabled):

```sql
SET ENABLE_NESTLOOP to FALSE;
```

## Conversion notes

- Two-star (manual) feature compatibility: SQL Server has a rich, statement-level hint system; PostgreSQL has only coarse session-level planner toggles. No automatic conversion path.
- SQL Server JOIN hints (`LOOP`/`HASH`/`MERGE`) → PostgreSQL has no per-query equivalent; nearest approximation is session toggles like `ENABLE_NESTLOOP`, `ENABLE_HASHJOIN`, `ENABLE_MERGEJOIN`.
- SQL Server `INDEX=`/`FORCESEEK` (force index use) → PostgreSQL has no index hint; influence indirectly with `SET ENABLE_SEQSCAN=FALSE` or by tuning `RANDOM_PAGE_COST`/`SEQ_PAGE_COST`.
- SQL Server `MAXDOP`, `OPTIMIZE FOR`, `RECOMPILE`, `FORCE ORDER`, `USE PLAN` → no direct PostgreSQL equivalents.
- SQL Server plan guides (apply hints without changing query text) → PostgreSQL has no native equivalent. On Aurora PostgreSQL, Query Plan Management (QPM) can enforce/manage plans for managed statements; the optional `pg_hint_plan` extension provides hint-style control but is not part of the playbook's standard approach.
- PostgreSQL session parameters reset at session end and affect the whole session, not a single statement — review their scope before relying on them in application code.
