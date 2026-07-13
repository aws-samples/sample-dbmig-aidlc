# Migrating Indexes to Aurora MySQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.indexes.html

**Conversion category:** Automatic (★★★★ feature compatibility, ★★★★ SCT automation)
**SCT automation:** AWS SCT action code — Indexes

Indexes are B-tree disk structures that optimize data access. SQL Server and Aurora
MySQL both implement B-tree indexes, but terminology, options, and limits differ. The
core migration concern is that **MySQL supports only clustered primary keys** and does
**not support filtered indexes or included (covering) columns**.

## SQL Server

SQL Server implements indexes with the Balanced Tree (B-tree) algorithm and also
supports hash, spatial, full-text, and XML index types. Up to 250 indexes per table.
Two B-tree types: clustered and nonclustered.

### Clustered indexes

Leaf level contains the entire row; the table data is physically sorted on disk. Only
one clustered index per table (it *is* the table). Created by default for primary keys.

```sql
-- Clustered index implicitly via PRIMARY KEY
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
);

-- Explicit clustered index
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY NONCLUSTERED,
    Col2 VARCHAR(20) NOT NULL
);
CREATE CLUSTERED INDEX IDX1 ON MyTable(Col2);
```

### Nonclustered indexes

Separate B-tree structure; leaf level holds row locators (RID for heaps, clustering key
for clustered tables). Up to 999 per table. May be UNIQUE.

```sql
-- Unique nonclustered via UNIQUE constraint
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL UNIQUE
);

-- Explicit unique nonclustered
CREATE UNIQUE NONCLUSTERED INDEX IDX1 ON MyTable(Col2);
```

### Filtered and covering indexes

Filtered indexes index only a subset of rows; covering indexes use `INCLUDE` to carry
extra non-key columns in the leaf to avoid lookups.

```sql
-- Filtered index (subset of rows)
CREATE NONCLUSTERED INDEX IDX1
ON MyTable(Col2)
WHERE Col2 IS NOT NULL;

-- Covering index (INCLUDE non-key column)
CREATE NONCLUSTERED INDEX IDX1
ON MyTable (Col2)
INCLUDE (Col3);
```

### Indexes on computed columns

Persisted computed columns can be indexed — useful to reshape predicates (e.g., reverse
a string so a `LIKE` wildcard moves to the end and can seek).

```sql
ALTER TABLE PhoneNumbers
ADD ReversePhone AS REVERSE(PhoneNumber) PERSISTED;

CREATE NONCLUSTERED INDEX IDX1
ON PhoneNumbers (ReversePhone)
INCLUDE (Customer);
```

## MySQL

Aurora MySQL supports B-tree indexes with different terminology and options. RDS for
MySQL 8 adds invisible indexes (maintained but ignored by the optimizer) and descending
indexes (`DESC` stores keys in descending order).

### Primary key indexes (clustered)

Created automatically for the primary key and are the equivalent of SQL Server clustered
indexes (entire row in the leaf). **Not configurable** — you cannot back a primary key
with a nonclustered index. A multi-column PK is a *Multiple Column index* (= composite).
PK indexes cannot be created with `CREATE INDEX`; use `CREATE TABLE` or
`ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY`; drop with `ALTER TABLE ... DROP PRIMARY KEY`.

If no PK is declared, MySQL picks the first all-NOT-NULL unique index as the clustered
index; failing that it generates a hidden `GEN_CLUST_INDEX` with internal row IDs.

```sql
-- Primary key index as part of table definition
CREATE TABLE MyTable (Col1 INT NOT NULL PRIMARY KEY, Col2 VARCHAR(20) NOT NULL);

-- Add primary key to an existing table (no need to name the constraint)
ALTER TABLE MyTable ADD CONSTRAINT PRIMARY KEY (Col1);
```

### Column and multiple-column secondary indexes

Single-column = SQL Server single-column nonclustered; multiple-column = composite
nonclustered. Default index type is `BTREE` (the `USING` clause is optional).

```sql
-- Unique B-tree as part of table definition
CREATE TABLE MyTable (Col1 INT NOT NULL PRIMARY KEY, Col2 VARCHAR(20) UNIQUE);

-- Non-unique multiple-column index on existing table
CREATE INDEX IDX1 ON MyTable (Col1, Col2) USING BTREE;
```

### Secondary indexes on generated columns

Equivalent of SQL Server computed columns. Generated columns are `STORED` or `VIRTUAL`,
but **indexes can only be created on `STORED` generated columns**. Generated expressions
cannot exceed 64 KB total per table.

### Prefix indexes

Index only the leading part of a string column. Optional for `CHAR`, `VARCHAR`,
`BINARY`, `VARBINARY`; **mandatory** for `BLOB` and `TEXT`. Prefix length is characters
for non-binary string types, bytes for binary types.

```sql
CREATE INDEX <Index Name> ON <Table Name> (<col name>(<prefix length>));

-- First ten characters of a customer name
CREATE INDEX PrefixIndex1 ON Customers (CustomerName(10));
```

## Conversion notes

- **Clustered indexes:** SQL Server allows clustered indexes on any table key (composite
  or single, unique or non-unique, null or not null). Aurora MySQL clusters on the
  **primary key only** and it is not configurable. Map a SQL Server clustered index that
  is not the PK to either the PK (if appropriate) or a secondary index.
- **Filtered indexes → not supported.** Aurora MySQL has no filtered-index equivalent;
  rework the query/index design (e.g., narrow the table, or rely on full secondary
  indexes).
- **Included (covering) columns → not supported.** Add the required columns as actual
  **index key columns** instead of `INCLUDE` columns.
- **Computed → generated columns:** SQL Server persisted computed columns map to MySQL
  `STORED` generated columns; only `STORED` (not `VIRTUAL`) generated columns are
  indexable.
- **Index name uniqueness:** MySQL does not require explicitly named constraints.
- **BLOB/TEXT:** MySQL supports indexes on BLOBs (limited by max key size) via mandatory
  prefix lengths; SQL Server does not index BLOBs.

### Summary table — key differences

| Index feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Clustered indexes supported for | Table keys, composite or single column, unique and non-unique, null or not null. | Primary keys only. | |
| Non-clustered index supported for | Table keys, composite or single column, unique and non-unique, null or not null. | Unique constraints, single column and multicolumn. | |
| Max number of non-clustered indexes | 999. | 64. | |
| Max total index key size | 900 bytes. | 3072 bytes for 16 KB page size, 1536 bytes for 8 KB page size, 768 bytes for 4 KB page size. | |
| Max columns for each index | 32. | 16. | |
| Index prefix | N/A. | Optional for `CHAR`, `VARCHAR`, `BINARY`, `VARBINARY`. Mandatory for `BLOB` and `TEXT`. | |
| Filtered indexes | Supported. | N/A. | |
| Included columns | Supported. | N/A. | Add the required columns as index key columns instead of included. |
| Indexes on BLOBs | N/A. | Supported, limited by maximal index key size. | |
