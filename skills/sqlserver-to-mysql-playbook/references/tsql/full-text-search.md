# Full-text search for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.fulltextsearch.html

**Conversion category:** Manual (Two star feature compatibility — no automation; requires rewrite)
**SCT automation:** No automation

## SQL Server

SQL Server runs full-text queries against character data via an integrated full-text engine and the `fdhost.exe` filter daemon. Requires a full-text catalog (logical container, single-database scope) containing one or more full-text indexes.

Full-text indexes can be created on columns of types: `CHAR`, `VARCHAR`, `NCHAR`, `NVARCHAR`, `TEXT`, `NTEXT`, `IMAGE`, `XML`, `VARBINARY(MAX)`, `FILESTREAM`. Up to 1024 columns per index.

Query predicates/functions: `CONTAINS`, `FREETEXT` (predicates); `CONTAINSTABLE`, `FREETEXTTABLE` (table-valued). (Don't confuse with `LIKE`, which is pattern matching only.) Search types: simple term, prefix, generational (inflectional), proximity, thesaurus/synonym, weighted.

Indexes auto-update by default; can be turned off and updated manually/scheduled for large changes. Monitor via `FULLTEXTCATALOGPROPERTY(<catalog>, 'Populatestatus')`.

### Examples

```sql
CREATE TABLE ProductReviews
(
    ReviewID INT NOT NULL IDENTITY(1,1),
    CONSTRAINT PK_ProductReviews PRIMARY KEY(ReviewID),
    ProductID INT NOT NULL,
    ReviewText VARCHAR(4000) NOT NULL,
    ReviewDate DATE NOT NULL,
    UserID INT NOT NULL
);

CREATE FULLTEXT CATALOG ProductFTCatalog;

CREATE FULLTEXT INDEX
ON ProductReviews (ReviewText)
KEY INDEX PK_ProductReviews
ON ProductFTCatalog;

SELECT *
FROM ProductReviews
WHERE CONTAINS(ReviewText, 'excellent');
```

## MySQL

Aurora MySQL supports InnoDB full-text indexes queried with the `MATCH … AGAINST` predicate. Indexes allowed on `CHAR`, `VARCHAR`, `TEXT` columns; created via `CREATE TABLE`, `ALTER TABLE`, or `CREATE INDEX`. Uses an inverted-index design with byte offsets for proximity. Index system tables visible via `INFORMATION_SCHEMA.INNODB_SYS_TABLES`.

Key internals:
- **Index cache** batches recent inserts to reduce auxiliary-table contention.
- **FTS_DOC_ID column** required; if absent, Aurora adds it on index creation, triggering a full table rebuild (warning `Code 124`). Create it explicitly (ideally `AUTO_INCREMENT`) before loading large tables. Dropping the index does not drop `FTS_DOC_ID`.
- **Deletes** are soft-logged in an internal `FTS_*_DELETED` table; run `OPTIMIZE TABLE` with `innodb_optimize_fulltext_only=ON` to rebuild.
- **Transactions**: full-text INSERT/UPDATE committed on transaction commit; search sees only committed data.

### MATCH… AGAINST syntax

```sql
MATCH (<Column List>)
AGAINST (
<String Expression>
[ IN NATURAL LANGUAGE MODE
    | IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION
    | IN BOOLEAN MODE
    | WITH QUERY EXPANSION]
)
```

Search string must be constant (no table column). Three search types:

- **Natural language** (default / `IN NATURAL LANGUAGE MODE`): interprets as human phrase, applies stop-word list, returns relevance.
- **Boolean** (`IN BOOLEAN MODE`): operators `+`/`-` (must/must-not contain), `@distance`, `<`/`>` (relevance weight), `()` grouping, `~` (negative weight), `*` (wildcard suffix), `"..."` (exact phrase).
- **Query expansion** (`WITH QUERY EXPANSION`): two-pass blind feedback for short queries.

### Examples

```sql
CREATE TABLE ProductReviews
(
    ReviewID INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    ProductID INT NOT NULL,
    ReviewText TEXT(4000) NOT NULL,
    ReviewDate DATE NOT NULL,
    UserID INT NOT NULL
);

-- Boolean: contains 'Excellent' but not 'England'
SELECT *
FROM ProductReviews
WHERE MATCH (ReviewText) AGAINST ('+Excellent -England' IN BOOLEAN MODE);

-- Natural language
SELECT *
FROM ProductReviews
WHERE MATCH (ReviewText) AGAINST ('Excellent' IN NATURAL LANGUAGE MODE);

-- warning when FTS_DOC_ID is added via ALTER/CREATE INDEX
CREATE FULLTEXT INDEX FTIndex1 ON TestFT(TextColumn);
SHOW WARNINGS;
-- Warning  124  InnoDB rebuilding table to add column FTS_DOC_ID.
```

## Conversion notes

- Full rewrite required for creation, management, and querying.
- Replace `CONTAINS`/`FREETEXT`/`CONTAINSTABLE`/`FREETEXTTABLE` with `MATCH … AGAINST` (natural/boolean/query-expansion modes).
- Aurora full-text is simpler and less comprehensive but sufficient for most basic needs.
- Pre-create the `FTS_DOC_ID` column (AUTO_INCREMENT) to avoid expensive table rebuilds on large tables.
- Maintain soft-deleted entries via `OPTIMIZE TABLE` + `innodb_optimize_fulltext_only=ON`.
- For complex workloads, consider Amazon CloudSearch (34 languages, highlighting, autocomplete, geospatial); no direct tooling integration — requires a custom sync app.
