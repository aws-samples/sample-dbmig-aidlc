# Query Hints and Plan Guides

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tuning.queryhints.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Three star automation level (SCT action code index: Query Hints)

Key difference: hint frameworks differ significantly between the two engines.

## SQL Server

SQL Server *hints* are instructions that override automatic choices made by the query processor for DML and DQL statements. Despite the name, a hint forces an override of any other run plan choice.

### JOIN Hints

Add `LOOP`, `HASH`, `MERGE`, and `REMOTE` hints to a `JOIN` — e.g., `… Table1 INNER LOOP JOIN Table2 ON …`. These force nested loops, hash match, or merge physical join algorithms. `REMOTE` enables processing a join with a remote table on the local server.

### Table Hints

Override the default behavior of the optimizer to force a particular locking strategy or access method for a table operation clause. They apply only for the duration of the DML/DQL statement. Common examples: `INDEX = <Index value>`, `FORCESEEK`, `NOLOCK`, `TABLOCKX`.

### Query Hints

Affect the entire set of query operators, not just the clause they appear in. May be JOIN hints, table hints, or query-only hints. Common ones: `OPTIMIZE FOR`, `RECOMPILE`, `FORCE ORDER`, `FAST <rows>`. Specified after the query, following the `WITH` options clause.

### Plan Guides

Provide functionality similar to query hints but are associated with a query without modifying its text — useful when you can't change the source code (e.g., third-party software, one-time ad-hoc queries). A plan guide consists of the statement plus either an `OPTION` clause of query hints or a full fixed XML query plan. At runtime SQL Server matches the query text and attaches the OPTION hints or the provided plan.

Three types:
- **Object plan guides** — target statements running within the scope of a code object (stored procedure, function, trigger). Not applied if the same statement appears in another context.
- **SQL plan guides** — match general ad-hoc statements not within code-object scope; applied to any instance regardless of originating client.
- **Template plan guides** — abstract statement templates that differ only in parameter values; can override the `PARAMETERIZATION` database option for a family of queries.

### Syntax

Query hints (shown for `SELECT`; usable in all DQL/DML statements):

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

Plan guide:

```sql
EXECUTE sp_create_plan_guide @name = '<Plan Guide Name>'
    ,@stmt = '<Statement>'
    ,@type = '<OBJECT|SQL|TEMPLATE>'
    ,@module_or_batch = 'Object Name>'|'<Batch Text>'| NULL
    ,@params = '<Parameter List>'|NULL }
    ,@hints = 'OPTION(<Query Hints>'|'<XML Plan>'|NULL;
```

### Examples

Limit parallelism for a sales report query:

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

Table and query hints:

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

## MySQL

Amazon Aurora MySQL supports two types of hints: **optimizer hints** and **index hints**. Unlike SQL Server, MySQL has no feature similar to plan guides.

### Index Hints

Placed directly after the table name (as in SQL Server) but with different keywords.

```sql
SELECT ...
FROM <Table Name>
    USE {INDEX|KEY}
        [FOR {JOIN|ORDER BY|GROUP BY}] (<Index List>)
    | IGNORE {INDEX|KEY}
        [FOR {JOIN|ORDER BY|GROUP BY}] (<Index List>)
    | FORCE {INDEX|KEY}
        [FOR {JOIN|ORDER BY|GROUP BY}] (<Index List>)
...n
```

- `USE INDEX` limits the optimizer to one of the listed indexes (allow list); `IGNORE` adds indexes to the deny list.
- `FORCE INDEX` is like `USE INDEX (index_list)` but strongly favors seek over scan (similar to SQL Server `FORCESEEK`), though the optimizer can still choose a scan if no other option is valid.
- Hints use actual index names, not column names. Refer to primary keys with the keyword `PRIMARY`. (In Aurora MySQL, the primary key is the clustered index.)
- Omitting `<Index List>` is allowed only for `USE INDEX` — it means use no indexes (equivalent to a clustered index scan).
- Scope down with `FOR JOIN`, `FOR ORDER BY`, or `FOR GROUP BY`.
- Multiple index hints can be specified for the same or different scope.

### Optimizer Hints

Specified within the statement text as a comment with a `+` prefix.

```sql
SELECT /*+ <Optimizer Hints> */ <Select List>...
INSERT /*+ <Optimizer Hints> */ INTO <Table>...
REPLACE /*+ <Optimizer Hints> */ INTO <Table>...
UPDATE /*+ <Optimizer Hints> */ <Table> SET...
DELETE /*+ <Optimizer Hints> */ FROM <Table>...
```

Scopes (widest to narrowest): Global, Query-level (query block in `UNION`/subquery), Table-level, Index-level.

| Hint name | Description | Applicable scopes |
|---|---|---|
| `BKA`, `NO_BKA` | Turns on or off Batched Key Access join processing | Query block, table |
| `BNL`, `NO_BNL` | Turns on or off Block Nested-Loop join processing | Query block, table |
| `MAX_EXECUTION_TIME` | Limits statement run time (seconds, always global) | Global |
| `MRR`, `NO_MRR` | Turns on or off multi-range read optimization | Table, index |
| `NO_ICP` | Turns off index condition push-down optimization | Table, index |
| `NO_RANGE_OPTIMIZATION` | Turns off range optimization | Table, index |
| `QB_NAME` | Assigns a logical name to a query block | Query block |
| `SEMIJOIN`, `NO_SEMIJOIN` | Turns on or off semi-join strategies | Query block |
| `SUBQUERY` | Determines `MATERIALIZATION` and `INTOEXISTS` processing | Query block |

Use `QB_NAME` to name a query block, then reference it with `@` to scope a hint to named subqueries:

```sql
SELECT /*+ SEMIJOIN(@SubQuery1 FIRSTMATCH, LOOSESCAN) */ *
FROM Table1
WHERE Col1 IN (SELECT /*+ QB_NAME(SubQuery1) */ Col1
FROM t3);
```

> `MAX_EXECUTION_TIME` is measured in seconds and is always global. SQL Server has no equivalent statement-scoped limit (its run-time limit is session-scoped).

### Migration Considerations

- Aurora MySQL's hint framework is relatively limited compared to SQL Server's granular control. SQL Server-specific optimizations may be inapplicable to a different optimizer.
- **Recommended approach:** start migration testing with all hints removed, then selectively apply hints only as a last resort after schema, index, and query optimizations have failed.
- Aurora MySQL uses allow/deny lists (`USE`/`IGNORE`) rather than SQL Server's explicit index approach.
- Index hints aren't mandatory in Aurora MySQL — the optimizer may choose alternatives if it can't use the hinted index. In SQL Server, forcing an invalid index or access method raises an error.

### Examples

Force an index access:

```sql
SELECT * FROM Table1 USE INDEX (Index1) ORDER BY Col1;
```

Multiple index hints:

```sql
SELECT * FROM Table1 USE INDEX (Index1) INNER JOIN Table2 IGNORE INDEX(Index2) ON
Table1.Col1 = Table2.Col1 ORDER BY Col1;
```

Optimizer hints:

```sql
SELECT /*+ NO_RANGE_OPTIMIZATION(Table1 PRIMARY, Index2) */ Col1 FROM Table1 WHERE
Col2 = 300;
```

```sql
SELECT /*+ BKA(t1) NO_BKA(t2) */ * FROM Table1 INNER JOIN Table2 ON ...;
```

```sql
SELECT /*+ NO_ICP(t1, t2) */ * FROM Table1 INNER JOIN Table2 ON ...;
```

## Conversion notes

- Two-star feature compatibility with three-star SCT automation (SCT action code: Query Hints).
- **Plan guides have no Aurora MySQL equivalent** — both "force a specific plan" and "apply hints to a query at runtime" are N/A in Aurora MySQL.
- Join hints: SQL Server `LOOP`/`MERGE`/`HASH` map loosely to Aurora MySQL `BNL`/`NO_BNL` (block-nested loops).
- Locking hints: supported in SQL Server, N/A in Aurora MySQL.
- Force seek/scan: SQL Server `FORCESEEK`/`FORCESCAN` → Aurora MySQL `FORCE INDEX`, or `USE INDEX` with no index list to force a clustered index scan.
- Force an index: SQL Server `INDEX=` → Aurora MySQL `USE`.
- Allow/deny list indexes: N/A in SQL Server; supported in Aurora MySQL via `USE` and `IGNORE`.
- Parameter value hints (`OPTIMIZE FOR`) and compilation hints (`RECOMPILE`): N/A in Aurora MySQL.
