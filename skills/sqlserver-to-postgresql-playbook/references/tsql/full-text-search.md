# Full-Text Search

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.fulltextsearch.html

**Conversion category:** Manual (two-star feature compatibility, no automation — full rewrite required)
**SCT automation:** No automation; SCT action code index: Full-Text Search

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Fixed the example (trigram index cannot serve @@; Aurora default_text_search_config is 'simple'), SERIAL→identity, STORED generated tsvector (VIRTUAL cannot be indexed, verified), CONTAINS/FREETEXT mappings, extension availability, CloudSearch→OpenSearch.

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
( ReviewID   int GENERATED ALWAYS AS IDENTITY PRIMARY KEY, ProductID INT NOT NULL,
  ReviewText text NOT NULL, ReviewDate DATE NOT NULL, UserID INT NOT NULL,
  ReviewTsv  tsvector GENERATED ALWAYS AS (to_tsvector('english', ReviewText)) STORED );

CREATE INDEX productreviews_tsv_gin ON ProductReviews USING gin (ReviewTsv);

-- CONTAINS(ReviewText, 'excellent')
SELECT * FROM ProductReviews WHERE ReviewTsv @@ to_tsquery('english', 'excellent');
```

> Correction (verified on Aurora PostgreSQL 18.6): the original example built a `gin_trgm_ops` (trigram) index and queried it with `@@ to_tsquery(...)`. A trigram index serves `LIKE`/`ILIKE`/`%`/similarity, **not** `@@`, so that query does a sequential scan. `text @@ tsquery` also silently uses `default_text_search_config`, which is `pg_catalog.simple` on Aurora (no stemming). Always name the configuration and index the same expression you query.

**PostgreSQL 18 notes (verified on 18.6):**
- Use a **STORED** generated `tsvector` column (replaces the trigger the playbook mentions) or an expression index `USING gin (to_tsvector('english', ReviewText))`. Do not use a PG 18 `VIRTUAL` generated column here: `CREATE INDEX` on it fails with "indexes on virtual generated columns are not supported".
- `websearch_to_tsquery('english', 'excellent -terrible "works great"')` accepts Google-style input and is the closest match to `FREETEXT`. `plainto_tsquery` / `phraseto_tsquery` cover simple-term and phrase `CONTAINS`.
- Prefix terms `CONTAINS(col, '"excel*"')` → `to_tsquery('english', 'excel:*')`; `NEAR` → `<N>`; weighted terms → `setweight()` + `ts_rank`/`ts_rank_cd`; `CONTAINSTABLE … RANK` → `ts_rank`; highlighting → `ts_headline`.
- Thesaurus/inflectional → `CREATE TEXT SEARCH DICTIONARY` (synonym, thesaurus, ispell). Accent-insensitive → `unaccent` extension.
- Available extensions on 18.6: `pg_trgm` 1.6 (substring `LIKE '%x%'`, fuzzy matching), `pg_bigm` 1.2 (2-gram, better for CJK text), `btree_gin` 1.3, `unaccent`, `dict_int`. `rum` and `pgroonga` are **not** available.
- Documents in `VARBINARY`/`FILESTREAM` (Word, PDF) are not parsed in the database; extract text in the application or with Amazon Textract before loading.
- For search beyond these features, use **Amazon OpenSearch Service** (an OpenSearch Ingestion pipeline can stream CDC from Aurora PostgreSQL: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/configure-client-aurora.html). Amazon CloudSearch, mentioned by the original playbook, is closed to new customers.

You can also create a text search dictionary (`CREATE TEXT SEARCH DICTIONARY`). For complex workloads, use **Amazon CloudSearch** (34 languages, highlighting, autocomplete, geospatial) — no direct Aurora integration, so build a custom sync application.

## Conversion notes
- Full rewrite required — different paradigm and syntax.
- Aurora PostgreSQL FTS is simpler and less comprehensive than SQL Server but sufficient for common needs.
- Map `CONTAINS`/`FREETEXT` → `@@` with `to_tsquery`/`to_tsvector`; catalogs/indexes → GIN/GiST indexes on `tsvector`.
- Maintain the `tsvector` with a STORED generated column (or an expression GIN index) instead of a trigger.
- `btree_gin` extension enables multi-column GIN indexes; `gin_trgm_ops` (pg_trgm) indexes `LIKE`/`ILIKE` patterns, not `@@`.
- For enterprise-scale search, use Amazon OpenSearch Service.
