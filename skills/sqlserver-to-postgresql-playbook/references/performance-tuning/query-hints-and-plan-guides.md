# Query Hints and Plan Guides

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tuning.queryplanning.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): QPM as the plan-guide equivalent (verified), `pg_hint_plan` 1.8 with a SQL Server → hint mapping (verified), drop-hints default, `NOLOCK` handling, statement-scoped settings.

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

Core PostgreSQL does not support in-query hints. On **Aurora PostgreSQL 18** there are three tools, in order of preference:

1. **Remove the hint and fix the cause** (statistics, indexes, query shape). Most SQL Server hints compensate for SQL Server optimizer behavior and are not needed.
2. **Aurora Query Plan Management (QPM, `apg_plan_mgmt`)**, the equivalent of **plan guides / `USE PLAN` / Query Store plan forcing**. It captures plans and enforces approved ones **without changing query text**. Enable with `rds.enable_plan_management = 1` in the cluster parameter group, then `CREATE EXTENSION apg_plan_mgmt;` (verified on 18.6).
3. **`pg_hint_plan`** (1.8.0 on Aurora 18; add to `shared_preload_libraries`, then `CREATE EXTENSION pg_hint_plan`). Comment hints at the **start** of the statement, verified on 18.6:
   ```sql
   /*+ IndexScan(t1 ix_t1_date) NestLoop(t1 t2) Leading((t1 t2)) Set(max_parallel_workers_per_gather 0) */
   SELECT * FROM mytable1 t1 JOIN mytable2 t2 ON t1.col1 = t2.col1 WHERE t1.date >= now() - interval '7 days';
   ```
   | SQL Server | `pg_hint_plan` |
   |---|---|
   | `WITH (INDEX = ix)` / `FORCESEEK` | `IndexScan(t ix)` |
   | `WITH (FORCESCAN)` | `SeqScan(t)` |
   | `INNER LOOP/HASH/MERGE JOIN` | `NestLoop(a b)` / `HashJoin(a b)` / `MergeJoin(a b)` |
   | `OPTION (FORCE ORDER)` | `Leading((a b c))` |
   | `OPTION (MAXDOP n)` | `Parallel(t n)` or `Set(max_parallel_workers_per_gather n)` |
   | `OPTION (RECOMPILE)` | no hint; `SET plan_cache_mode = force_custom_plan` for the session/function |
   | `OPTION (OPTIMIZE FOR …)` | no equivalent; QPM to pin a plan |
   | `NOLOCK`, `TABLOCKX`, `HOLDLOCK` | not optimizer hints: drop `NOLOCK` (MVCC readers never block); use `LOCK TABLE` / `SELECT … FOR UPDATE` or `SERIALIZABLE` for the locking intent |

Session parameters (Query Planning Parameters) can also influence the optimizer at the session level:

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
- SQL Server plan guides (apply hints without changing query text) → **Aurora QPM** (approved plans per statement). `pg_hint_plan` also has a `hint_plan.hints` table that attaches hints to normalized query text without changing the application, which is a closer analog to SQL plan guides.
- **Default conversion: drop hints** and record each one in the conversion log. Re-add only those that a performance test proves necessary, preferably as QPM-approved plans.
- `NOLOCK` / `READUNCOMMITTED` table hints can always be dropped safely: PostgreSQL readers never block writers and never see uncommitted data.
- PostgreSQL session parameters reset at session end and affect the whole session, not a single statement — review their scope before relying on them in application code. Prefer `SET LOCAL` inside a transaction, `ALTER FUNCTION … SET …` for one routine, or a `pg_hint_plan` `Set(...)` hint for one statement.
