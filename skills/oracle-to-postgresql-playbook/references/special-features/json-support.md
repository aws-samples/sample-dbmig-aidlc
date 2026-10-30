# JSON Support

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.json.html

**Conversion category:** Assisted (the playbook rated this two-star for PG ≤ 15; on PostgreSQL 17/18 the SQL/JSON standard functions make Oracle `JSON_VALUE`/`JSON_QUERY`/`JSON_EXISTS`/`JSON_TABLE`/`IS JSON` mostly direct conversions)
**SCT automation:** N/A. Key difference: different paradigm and syntax will require application or driver rewrite.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 16/17 SQL/JSON functions (`JSON_VALUE`/`JSON_QUERY`/`JSON_EXISTS`/`JSON_TABLE`/`IS JSON`/constructors), all verified on 18.6, with an Oracle mapping table; fixed broken index examples; `uuidv7()` for SYS_GUID keys.

## Oracle

Oracle stores JSON in `VARCHAR2`, `CLOB`, or `BLOB` columns (unlike XML which uses `XMLType`). Oracle recommends an `IS JSON` check constraint. Oracle 19 adds `JSON_SERIALIZE`. SQL functions include `IS JSON`, `JSON_VALUE`, `JSON_EXISTS`, `JSON_QUERY`, `JSON_TABLE`.

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

Query with **dot notation** (no special functions):
```sql
SELECT a.data.FName,a.data.LName,a.data.Address.Pcode AS Postcode
FROM json_docs a;
```

## PostgreSQL

Native JSON support via two data types:
- **JSON** — stores exact text copy; re-parsed on each operation; preserves whitespace and key order.
- **JSONB** — decomposed binary format; slightly slower input, much faster reads (no re-parsing). Does not preserve whitespace, key order, or duplicate keys (keeps last). Most apps use JSONB.

Both support full-text search since PG 10. For full JSON spec compliance, database encoding must be UTF8.

### SQL/JSON standard functions (PG 16/17, verified on Aurora PostgreSQL 18.6)

These match Oracle's SQL/JSON functions, so most Oracle JSON SQL converts with little change:

| Oracle | PostgreSQL 18 | Notes |
|---|---|---|
| `col IS JSON` (check constraint) | `col IS JSON [OBJECT\|ARRAY\|SCALAR] [WITH UNIQUE KEYS]` (PG 16) | Use a `jsonb` column; the type already rejects invalid JSON |
| `JSON_VALUE(doc, '$.a.b' RETURNING NUMBER DEFAULT -1 ON ERROR)` | `json_value(doc, '$.a.b' RETURNING int DEFAULT -1 ON ERROR)` (PG 17) | `ON EMPTY` / `ON ERROR` clauses supported |
| `JSON_QUERY(doc, '$.a')` | `json_query(doc, '$.a' [WITH WRAPPER])` (PG 17) | |
| `JSON_EXISTS(doc, '$.a')` | `json_exists(doc, '$.a')` (PG 17) | |
| `JSON_TABLE(doc, '$[*]' COLUMNS (… NESTED PATH …))` | `json_table(doc, '$[*]' COLUMNS (id int PATH '$.id', NESTED PATH '$.l[*]' COLUMNS (…), ord FOR ORDINALITY))` (PG 17) | |
| `JSON_OBJECT('a' VALUE 1)`, `JSON_ARRAY`, `JSON_ARRAYAGG`, `JSON_OBJECTAGG` | Same names (PG 16) | |
| `JSON_SERIALIZE`, `JSON(...)`, `JSON_SCALAR` | Same names (PG 17) | |
| Dot notation `t.doc.Address.Pcode` | **Not supported** (`missing FROM-clause entry`, verified) → `json_value(doc, '$.Address.Pcode')` or `doc->'Address'->>'Pcode'` | |
| `SYS_GUID()` keys (`RAW(16)`) | `uuid` with `DEFAULT uuidv7()` (PG 18) or `gen_random_uuid()` | `uuidv7` is time-ordered, which suits B-tree indexes |

Query examples (PostgreSQL-native syntax — application queries must change):
```sql
SELECT emp_data FROM employees WHERE emp_id = 1;

-- has key 'address'
SELECT emp_data FROM employees WHERE emp_data ? 'address';

-- has any of these keys
SELECT * FROM employees WHERE emp_data ?| array['address', 'hobbies'];

-- has all of these keys
SELECT * FROM employees WHERE emp_data ?& array['a', 'b'];

-- navigate nested values
SELECT emp_data ->'phone numbers'->>'home' FROM employees;

-- equality / like on extracted text
SELECT * FROM employees WHERE emp_data->>'address' = '1234 First Street, Capital City';
SELECT * FROM employees WHERE emp_data->>'address' like '%Capital City%';

-- containment operator
select '{"id":132, "name":"John"}'::jsonb @> '{"id":132}'::jsonb;

-- concatenate
select '{"id":132, "fname":"John"}'::jsonb || '{"lname":"Doe"}'::jsonb;

-- remove keys
select '{"id":132, "fname":"John", "salary":999999,
  "bank_account":1234}'::jsonb - '{salary,bank_account}'::text[];
```

**Indexing and constraints on JSONB:**
```sql
-- unique constraint on a key
CREATE UNIQUE INDEX employee_address_uq ON employees( (emp_data->>'address') );

-- expression index on a key
CREATE INDEX idx1_employees ON employees ((emp_data->>'address'));

-- GIN indexes (support @>, ?, ?&, ?| operators)
CREATE INDEX idx2_employees ON employees USING gin ((emp_data->'tags'));
CREATE INDEX idx3_employees ON employees USING gin (emp_data);
-- smaller/faster GIN when you only use @> and jsonpath (@?, @@):
CREATE INDEX idx4_employees ON employees USING gin (emp_data jsonb_path_ops);
```
PostgreSQL supports B-Tree, HASH, and GIN indexes for JSON. Without indexes, JSON filtering forces full table scans (steps into each document), hurting performance.

### Summary mapping

| Feature | Oracle | Aurora PostgreSQL |
|---|---|---|
| Return full JSON document | `SELECT emp_data FROM employees;` | `SELECT emp_data FROM employees;` |
| Return a specific element | `SELECT e.emp_data.address FROM employees e;` | `SELECT emp_data->>'address' from employees where emp_id = 1;` |
| Pattern match any field | `SELECT e.emp_data FROM employees e WHERE e.emp_data like '%pattern%';` | `SELECT * from (select jsonb_pretty(emp_data) as raw_data from employees) raw_jason where raw_data like '%1234%';` or `SELECT key, value FROM card, lateral jsonb_each_text(data) WHERE value LIKE '%pattern%';` |
| Pattern match specific (root) field | `SELECT e.emp_data.name FROM employees e WHERE e.data.active = 'true';` | `SELECT * FROM employees WHERE emp_data->>'active' = 'true';` |
| Define JSON column | CLOB column + `IS JSON` constraint | `CREATE TABLE json_docs (id uuid PRIMARY KEY DEFAULT uuidv7(), data jsonb CHECK (data IS JSON OBJECT));` |
| Extract scalar with type | `JSON_VALUE(data, '$.Address.Pcode')` | `json_value(data, '$.Address.Pcode')` (PG 17+) |
| Relational projection | `JSON_TABLE(...)` | `json_table(...)` (PG 17+) |

## Conversion notes
- On Aurora PostgreSQL 17/18, **convert Oracle SQL/JSON functions one-to-one** (`JSON_VALUE`, `JSON_QUERY`, `JSON_EXISTS`, `JSON_TABLE`, `IS JSON`, constructors). Their jsonpath syntax is the same SQL-standard language. Check `RETURNING` types and `ON ERROR`/`ON EMPTY` defaults: when no clause is given, both engines return NULL on error.
- Oracle dot-notation queries must be rewritten. Prefer `json_value(...)` for portability with the Oracle text, or operators (`->`, `->>`, `#>>`, `?`, `?|`, `?&`, `@>`) when an index must be used: GIN indexes serve `@>`, `?`, `@?`, `@@`, not `json_value`. Expression B-tree indexes on `(data->>'key')` serve equality and range filters.
- Prefer **JSONB** over JSON for performance; use **GIN** indexes for containment/key-existence queries.
- Enforce uniqueness/constraints via expression `CREATE UNIQUE INDEX` on extracted keys.
- Set database encoding to UTF8 for full JSON spec compliance.
