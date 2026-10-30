# Storage for Aurora MySQL (Partitioning)

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.storage.html

**Conversion category:** Manual (Three star feature compatibility, No automation)
**SCT automation:** N/A — AWS SCT action code index: Partitioning

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Fixed the subpartition example; added verified restrictions (unique keys must include partition columns — 1503; no FKs — 1506; HASH needs integers — 1659), RANGE LEFT boundary conversion, REORGANIZE splitting any partition, partition-level DML, event-based sliding windows.

Aurora MySQL offers more partition types than SQL Server but with more restrictions on partitioned tables.

## SQL Server

SQL Server provides a logical and physical framework for partitioning table and index data. Every table and index is partitioned, but may have only one partition. SQL Server 2017 supports up to 15,000 partitions. Partitioning separates data into logical units that can be stored in more than one file group. Partitioning is horizontal — sets of rows are mapped to individual partitions. A partitioned table or index is a single object residing in a single schema within a single database; objects of disjointed partitions aren't allowed.

All DQL/DML operations are partition agnostic except the special `$partition` predicate, used for explicit partition elimination.

Partitioning addresses management and performance challenges for large tables:
- Deleting/inserting large amounts of data via partition switching instead of row processing, while maintaining logical consistency.
- Maintenance operations split and customized per partition (e.g., compress old partitions, rebuild/reorganize active ones more frequently).
- Internal query optimizations such as collocated and parallel partitioned joins.
- Physical storage performance optimization by distributing IO across partitions and storage channels.
- Concurrency improvements via lock escalation to the partition level rather than the whole table.

SQL Server partitioning uses three objects:
- **Partitioning column** — the column(s) the partition function uses. Computed columns may be used if explicitly `PERSISTED`. Any valid index column data type < 900 bytes per key, except `timestamp` and LOB types.
- **Partition function** — defines how partitioning column values map to a logical partition, describing partitions and their boundaries.
- **Partition scheme** — maps logical partitions to a set of file groups (physical OS files). Placing partitions on individual file groups enables per-partition backup.

### Syntax

```sql
CREATE PARTITION FUNCTION <Partition Function>(<Data Type>)
AS RANGE [ LEFT | RIGHT ]
FOR VALUES (<Boundary Value 1>,...)[;]

CREATE PARTITION SCHEME <Partition Scheme>
AS PARTITION <Partition Function>
[ALL] TO (<File Group> | [ PRIMARY ] [,...])[;]

CREATE TABLE <Table Name> (<Table Definition>)
ON <Partition Schema> (<Partitioning Column>);
```

### Examples

Create a partitioned table:

```sql
CREATE PARTITION FUNCTION PartitionFunction1 (INT)
AS RANGE LEFT FOR VALUES (1, 1000, 100000);

CREATE PARTITION SCHEME PartitionScheme1
AS PARTITION PartitionFunction1
ALL TO (PRIMARY);

CREATE TABLE PartitionTable (
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20)
)
ON PartitionScheme1 (Col1);
```

## MySQL

Aurora MySQL supports a much richer partitioning framework than SQL Server, including hash partitioning, subpartitioning, and more — but introduces many restrictions on participating tables.

- Maximum partitions per table is 8,192 (including subpartitions) vs. 15,000 in SQL Server; practical partitioning rarely exceeds a few hundred.
- In Amazon RDS for MySQL 8, `ADD PARTITION`, `DROP PARTITION`, `COALESCE PARTITION`, `REORGANIZE PARTITION`, and `REBUILD PARTITION` ALTER TABLE options are supported by native in-place APIs and may use `ALGORITHM={COPY|INPLACE}` and `LOCK` clauses. `DROP PARTITION` with `ALGORITHM=INPLACE` deletes the partition's data and drops it; with `ALGORITHM=COPY` (or `old_alter_table=ON`) it rebuilds the table and attempts to move data to another partition with a compatible `PARTITION … VALUES` definition (data that can't be moved is deleted).

Partition types supported:

- **Range Partitioning** — equivalent to SQL Server `RANGE` partition functions (the only SQL Server type). Explicit boundaries; each partition holds only rows whose partitioning expression value lies within the boundaries. Ranges must be contiguous and non-overlapping. Boundaries defined with `VALUES LESS THAN`.
- **List Partitioning** — resembles range; each partition defined explicitly, but using a set of value lists rather than a contiguous range. Use `PARTITION BY LIST(<Column Expression>)` (expression must return an integer); each partition uses `VALUES IN (<Value List>)` of comma-separated integers.
- **Range and List Columns Partitioning** — variant allowing multiple columns in partitioning keys; all column values considered for matching. Allows non-integer values. Supported types: all integer types; `DATE` and `DATETIME`; `CHAR`, `VARCHAR`, `BINARY`, `VARBINARY`.
- **Hash Partitioning** — guarantees even row distribution across a chosen number of partitions. Aurora MySQL manages values and partitions; specify only the column/expression to hash and the total partition count.
- **Subpartitioning (composite)** — each primary partition further partitioned into a two-layer hierarchy. Subpartitions must use HASH or KEY; only range or list partitions may be subpartitioned. SQL Server doesn't support subpartitions.

Partition management uses Aurora MySQL `ALTER TABLE` extensions:

- **Dropping** — range/list: `ALTER TABLE … DROP PARTITION`. Range: data deleted; new rows that would fit go to the immediate neighbor. List: data deleted; new rows that would fit can't be INSERTed/UPDATEd (no logical container). Hash/key: `ALTER TABLE … COALESCE PARTITION <N>` reduces total partitions by N.
- **Adding/Splitting** — `ALTER TABLE … ADD PARTITION` adds a new range boundary or list values. Range: new range may only be added to the end. Split **any** existing range partition with `ALTER TABLE … REORGANIZE PARTITION` (verified on a middle partition) — the equivalent of SQL Server `SPLIT RANGE`; `MERGE RANGE` → `REORGANIZE PARTITION p1, p2 INTO (…)`.
- **Switching/Exchanging** — `ALTER TABLE <Partitioned Table> EXCHANGE PARTITION <Partition> WITH TABLE <Non Partitioned Table>`. The non-partitioned table can't be temporary; schemas must be identical; it can't have/being a referenced FK. All rows must be within partition boundaries unless `WITHOUT VALIDATION` is used. Requires `ALTER`, `INSERT`, `CREATE`, `DROP` privileges. Does not fire triggers. `AUTO_INCREMENT` columns in the exchanged table are reset.

### Syntax

Create a partitioned table:

```sql
CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <Table Name>
(<Table Definition>) [<Table Options>]
PARTITION BY
{ [LINEAR] HASH(<Expression>)
    | [LINEAR] KEY [ALGORITHM={1|2}] (<Column List>)
    | RANGE{(expr) | COLUMNS(<Column List>)}
    | LIST{(expr) | COLUMNS(<Column List>)} }
[PARTITIONS <Number>]
[SUBPARTITION BY
    { [LINEAR] HASH(<Expression>)
    | [LINEAR] KEY [ALGORITHM={1|2}] (<Column List>) }
[SUBPARTITIONS <Number>]
```

Reorganize or split a partition:

```sql
ALTER TABLE <Table Name>
REORGANIZE PARTITION <Partition> INTO (
PARTITION <New Partition 1> VALUES LESS THAN (<New Range Boundary>),
PARTITION <New Partition 2> VALUES LESS THAN (<Range Boundary>)
);
```

Exchange a partition:

```sql
ALTER TABLE <Partitioned Table> EXCHANGE PARTITION <Partition> WITH TABLE <Non Partitioned Table>;
```

Drop a partition:

```sql
ALTER TABLE <Table Name> DROP PARTITION <Partition>;
```

### Examples

Create a range partitioned table:

```sql
CREATE TABLE MyTable (
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
)
PARTITION BY RANGE (Col1)
(
    PARTITION p0 VALUES LESS THAN (100000),
    PARTITION p1 VALUES LESS THAN (200000),
    PARTITION p2 VALUES LESS THAN (300000),
    PARTITION p3 VALUES LESS THAN (400000)
);
```

Create subpartitions:

```sql
CREATE TABLE MyTable (Col1 INT NOT NULL, DateCol DATE NOT NULL)   -- the original had a trailing comma
PARTITION BY RANGE(YEAR(DateCol))
SUBPARTITION BY HASH(TO_DAYS(DateCol))
SUBPARTITIONS 2 (
    PARTITION p0 VALUES LESS THAN (1990),
    PARTITION p1 VALUES LESS THAN (2000),
    PARTITION p2 VALUES LESS THAN MAXVALUE
);
```

Drop a range partition:

```sql
ALTER TABLE MyTable DROP PARTITION p2
```

Reduce the number of hash partitions by four:

```sql
ALTER TABLE <Table Name> COALESCE PARTITION 4;
```

Add range partitions:

```sql
ALTER TABLE MyTable ADD PARTITION (PARTITION p4 VALUES LESS THAN (50000));
```

## Conversion notes

- **No automation** — partitioning is a manual conversion (three-star compatibility).
- **Partition types**: SQL Server supports `RANGE` only; Aurora MySQL supports `RANGE`, `LIST`, `HASH`, `KEY`.
- **Partitioned tables scope**: In SQL Server all tables are partitioned (some with more than one partition); in Aurora MySQL tables are not partitioned unless explicitly defined.
- **Boundary direction**: SQL Server allows `LEFT` or `RIGHT`; Aurora MySQL is `RIGHT` only (determines which partition the boundary value itself goes to).
- **Exchange partition**: SQL Server can switch any partition to any partition; Aurora MySQL only exchanges a partition with a non-partitioned table (no partition-to-partition switch).
- **Partition function/scheme**: SQL Server uses abstract, reusable function and storage-mapping (file group) objects. Aurora MySQL defines partitioning per table; there is no partition scheme because physical storage is managed by Amazon RDS. File-group concepts don't apply.
- **Partitioning key types**: Aurora MySQL partitioning keys/expressions must be `INT` types and can't be `ENUM`; the expression may yield NULL. Exceptions: range/list COLUMNS partitioning allows strings, `DATE`, `DATETIME`; `[LINEAR] KEY` allows any valid MySQL type except `TEXT` and `BLOB`.
- **Restrictions**: Aurora MySQL partitioned tables can't use foreign keys (neither referencing nor referenced — error 1506, verified), `FULLTEXT` indexes, or spatial types (`POINT`, `GEOMETRY`). SQL Server has no such limits since all tables are partitioned.
- **Every PRIMARY KEY and UNIQUE key must include all partitioning columns** (error 1503, verified). SQL Server allows a non-aligned unique index; in MySQL uniqueness weakens to (key, partition column) — get sign-off, or don't partition.
- `HASH` needs an integer expression (`VARCHAR` → error 1659, verified); use `KEY` partitioning for strings.
- **LEFT-range partition functions:** SQL Server `RANGE LEFT FOR VALUES (100, 200)` puts the boundary value in the lower partition; MySQL `VALUES LESS THAN` puts it in the upper one. Convert boundaries to `LESS THAN (101)`, `(201)` for integers, or to the next date/day for date keys.
- Partition-level operations: `TRUNCATE TABLE … WITH (PARTITIONS (2))` → `ALTER TABLE … TRUNCATE PARTITION p2`; `$PARTITION.fn(col)` → query `information_schema.partitions` or `EXPLAIN` (`partitions` column); `SELECT … FROM t PARTITION (p2)` works (verified).
- Partitioning on a generated column works (verified), which covers partitioning by a computed expression.
- Sliding-window maintenance (SQL Server Agent job with `SPLIT`/`SWITCH`) → a MySQL `EVENT` (scheduler ON by default on Aurora, verified) running `REORGANIZE`/`EXCHANGE`/`DROP PARTITION`.
- See MySQL docs: Overview of Partitioning, Partition Management, Partitioning Types, and Restrictions and Limitations on Partitioning.
