# Oracle JSON Document Support and MySQL JSON

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.json.html

**Conversion category:** Assisted (three-star feature compatibility; three-star automation) — different paradigm/syntax requires application or driver rewrite.
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Added verified functional and multi-valued JSON indexes, JSON_SCHEMA_VALID check constraints, Oracle SQL/JSON function equivalents; fixed the dot-notation example (missing $.); ->> typing notes.

## Oracle

Oracle supports JSON storage and retrieval for semi-structured data, plus full-text search and JSON query functions. JSON is stored in `VARCHAR2`, `CLOB`, or `BLOB` columns (not a dedicated type). Oracle recommends an `IS JSON` check constraint to validate. Oracle 19 adds `JSON_SERIALIZE`.

Create a table and insert a JSON document:

```sql
CREATE TABLE json_docs (id RAW(16) NOT NULL, data CLOB,
CONSTRAINT json_docs_pk PRIMARY KEY (id),
CONSTRAINT json_docs_json_chk CHECK (data IS JSON));

INSERT INTO json_docs (id, data) VALUES (SYS_GUID(),
'{
  "FName" : "John",
  "LName" : "Doe",
  "Address" : {
    "Street" : "101 Street",
    "City" : "City Name",
    "Country" : "US",
    "Pcode" : "90210"}
}');
```

Query directly with dot notation (no special functions):

```sql
SELECT a.data.FName, a.data.LName, a.data.Address.Pcode AS Postcode
FROM json_docs a;
-- FNAME  LNAME  POSTCODE
-- John   Doe    90210
```

SQL JSON functions: `IS JSON`, `JSON_VALUE`, `JSON_EXISTS`, `JSON_QUERY`, `JSON_TABLE`, `IS_NOT_JSON`.

## MySQL

Aurora MySQL 5.7+ has a native `JSON` data type. Documents are validated on insert (invalid JSON is rejected); stored in an optimized binary representation enabling fast access without re-parsing.

```sql
CREATE TABLE JSONTable (
  DocumentIdentifier INT NOT NULL PRIMARY KEY,
  JSONDocument JSON);
```

Utility functions: `JSON_PRETTY()` (5.7.22), `JSON_STORAGE_SIZE()` / `JSON_STORAGE_FREE()` (5.7.22). MySQL 8 adds aggregation `JSON_ARRAYAGG()` / `JSON_OBJECTAGG()`, and 8.0.17 adds validation `JSON_SCHEMA_VALID()` / `JSON_SCHEMA_VALIDATION_REPORT()`.

Aurora MySQL has 25+ JSON functions for add/modify/search, plus spatial GeoJSON functions:

```sql
-- construct
SELECT JSON_OBJECT('Person', 'John', 'Country', 'USA');
-- {"Person": "John", "Country": "USA"}

-- extract / search
SELECT JSON_EXTRACT('["Mary", "Paul", ["Jim", "Ryan"]]', '$[1]');   -- "Paul"
SELECT JSON_SEARCH('["Mary", "Paul", ["Jim", "Ryan"]]', 'one', 'Paul');  -- "$[1]"

-- modify
SELECT JSON_ARRAY_INSERT('["Mary", "Paul", "Jim"]', '$[1]', 'Jack');
-- ["Mary", "Jack", "Paul", "Jim"]
```

Query/search functions: `JSON_CONTAINS`, `JSON_CONTAINS_PATH`, `JSON_EXTRACT`, `JSON_KEYS`, `JSON_SEARCH`. Modify functions: `JSON_INSERT`, `JSON_REMOVE`, `JSON_REPLACE` and ARRAY counterparts.

### JSON indexes

JSON columns cannot be indexed directly. Options on Aurora MySQL 3 / 8.4 (all verified on 3.13 and 8.4.8):
- **Generated column + index:** `addr VARCHAR(100) AS (d->>'$.address') STORED, INDEX (addr)`.
- **Functional index:** `INDEX ((CAST(d->>'$.address' AS CHAR(100)) COLLATE utf8mb4_bin))` — the expression in queries must match.
- **Multi-valued index** on a JSON array (8.0.17+): `INDEX ix_tags ((CAST(d->'$.tags' AS CHAR(20) ARRAY)))`, used by `MEMBER OF`, `JSON_CONTAINS` and `JSON_OVERLAPS` (verified: `EXPLAIN` shows *Index lookup on jt using ix_tags*).

Validation: invalid JSON is rejected on insert (error 3140, verified). Oracle `IS JSON` check constraints are implicit; Oracle JSON schema checks → `CHECK (JSON_SCHEMA_VALID('{…schema…}', d))` (verified, error 3819 on violation).

Oracle SQL/JSON functions that exist in MySQL 8: `JSON_VALUE(d, '$.a' RETURNING type)`, `JSON_TABLE`, `JSON_OBJECT`, `JSON_ARRAYAGG`/`JSON_OBJECTAGG`, `JSON_EXISTS` → `JSON_CONTAINS_PATH(d, 'one', '$.a')`, `JSON_QUERY` → `JSON_EXTRACT`/`->`, `JSON_MERGEPATCH` → `JSON_MERGE_PATCH` (verified).

## Conversion notes

- Storage model differs: Oracle stores JSON in `VARCHAR2`/`CLOB`/`BLOB` with an `IS JSON` constraint; MySQL has a validated native `JSON` type.
- Rewrite Oracle **dot-notation** access to MySQL operators/functions:
  - `SELECT e.emp_data.address FROM employees e;` → `SELECT emp_data->>'$.address' FROM employees;` (the path needs the `$.` prefix; the original example omitted it)
  - Field filter: `... WHERE e.data.active = 'true';` → `... WHERE emp_data->>"$.active" = 'true';`
- Returning the whole document is identical: `SELECT emp_data FROM employees;`
- Pattern search across all fields with `LIKE '%pattern%'` works the same in both.
- Indexing JSON requires a generated column, a functional index or a multi-valued index.
- `->>` returns text: booleans come back as `'true'`/`'false'` strings and numbers as text (verified); compare with `JSON_TYPE()` or `JSON_VALUE(… RETURNING …)` when the type matters.
- `->`/`->>` work only on column references; on a literal or expression use `JSON_EXTRACT`/`JSON_UNQUOTE`.
- MySQL `JSON` columns cannot have a non-expression default; use `DEFAULT (JSON_OBJECT())`.
- Oracle 21c native `JSON` type and `JSON_TRANSFORM` → `JSON` + `JSON_SET`/`JSON_REPLACE`/`JSON_REMOVE`.
- Application code and drivers relying on Oracle JSON functions need rewriting to MySQL's function set.
