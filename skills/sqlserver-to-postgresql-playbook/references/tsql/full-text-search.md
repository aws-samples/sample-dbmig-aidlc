# Full-Text Search

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.fulltextsearch.html

**Conversion category:** Manual (two-star feature compatibility, no automation — full rewrite required)
**SCT automation:** No automation; SCT action code index: Full-Text Search

## SQL Server

SQL Server provides an integrated in-process full-text engine (plus the `fdhost.exe` filter daemon) for linguistic searches against character data. You create a full-text catalog (logical container, single-database scope) holding one or more full-text indexes; an index covers one or more textual columns.

Supported column types for full-text indexes: `CHAR`, `VARCHAR`, `NCHAR`, `NVARCHAR`, `TEXT`, `NTEXT`, `IMAGE`, `XML`, `VARBINARY(MAX)`, `FILESTREAM`. Use `CREATE FULLTEXT INDEX` (up to 1024 columns). Binary columns can store/parse documents (e.g., Word).

Query types: simple term, prefix term, generational (inflectional), proximity, thesaurus (synonyms), weighted term. Predicates/functions: `CONTAINS`, `FREETEXT` predicates; `CONTAINSTABLE`, `FREETEXTTABLE` table-valued functions. (Not to be confused with `LIKE`.)

Indexes auto-update on data change; large changes can be costly, so you can disable auto-update and refresh manually/scheduled. Monitor via `FULLTEXTCATALOGPROPERTY(<catalog>, 'Populatestatus')`.

Examples:

```sql
CREATE FULLTEXT CATALOG ProductFTCatalog;

CREATE FULLTEXT INDEX
ON ProductReviews (ReviewText)
KEY INDEX PK_ProductReviews
ON ProductFTCatalog;

SELECT * FROM ProductReviews
WHERE CONTAINS(ReviewText, 'excellent');
```

## PostgreSQL

Full-text search uses the `@@` predicate. The default search class uses `tsvector`; typically you store text and convert to `tsvector` (often via triggers). Two index types: **GIN** (slower to build, no false positives, faster to query — improve build with higher `maintenance_work_mem`) and **GiST**.

GIN options: `fastupdate` (queue updates for VACUUM; default ON), `gin_pending_list_limit` (default 4MB). GIN can't be a composite (multi-column) index unless you add the `btree_gin` extension (supported in Aurora):

```sql
CREATE EXTENSION btree_gin;
CREATE INDEX reviews_idx ON reviews USING GIN (title, body);
```

Search functions — `to_tsquery()` checked against `to_tsvector()` with `@@`:

```sql
-- Boolean / simple match (matches 'boy','boys' but not 'boyser'):
SELECT to_tsvector('The quick young boy jumped over the fence') @@ to_tsquery('boy');

-- Operators: AND (&), OR (|), NOT (!):
SELECT to_tsvector('The quick young boy jumped over the fence')
@@ to_tsquery('young & (boy | guy) & !girl');

-- With language:
SELECT to_tsvector('The quick young boy jumped over the fence')
@@ to_tsquery('english', 'young & (boys | guy) & !girl');

-- Distance/phrase (<-> = adjacent, <N> = within N):
SELECT to_tsvector('The quick young boy jumped over the fence') @@ to_tsquery('young <-> boy'),
       to_tsvector('The quick young boy jumped over the fence') @@ to_tsquery('quick <3> jumped');
```

Example table + index + query:

```sql
CREATE TABLE ProductReviews
( ReviewID SERIAL PRIMARY KEY, ProductID INT NOT NULL,
  ReviewText TEXT NOT NULL, ReviewDate DATE NOT NULL, UserID INT NOT NULL );

CREATE INDEX gin_idx ON ProductReviews USING gin (ReviewText gin_trgm_ops);

SELECT * FROM ProductReviews where ReviewText @@ to_tsquery('excellent');
```

You can also create a text search dictionary (`CREATE TEXT SEARCH DICTIONARY`). For complex workloads, use **Amazon CloudSearch** (34 languages, highlighting, autocomplete, geospatial) — no direct Aurora integration, so build a custom sync application.

## Conversion notes
- Full rewrite required — different paradigm and syntax.
- Aurora PostgreSQL FTS is simpler and less comprehensive than SQL Server but sufficient for common needs.
- Map `CONTAINS`/`FREETEXT` → `@@` with `to_tsquery`/`to_tsvector`; catalogs/indexes → GIN/GiST indexes on `tsvector`.
- Use triggers to maintain a `tsvector` column for performance.
- `btree_gin` extension enables multi-column GIN indexes; `gin_trgm_ops` for trigram text indexing.
- For enterprise-scale search, offload to Amazon CloudSearch with a custom synchronization process.
