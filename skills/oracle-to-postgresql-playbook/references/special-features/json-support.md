# JSON Support

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.json.html

**Conversion category:** Assisted (Two-star feature compatibility, three-star automation)
**SCT automation:** N/A. Key difference: different paradigm and syntax will require application or driver rewrite.

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

Query examples (PostgreSQL-native syntax — application queries must change):
```sql
SELECT emp_data FROM employees WHERE emp_id = 1;

-- has key 'address'
SELECT emp_data FROM employees WHERE emp_data ? ' address';

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
CREATE idx1_employees ON employees ((emp_data->>'address'));

-- GIN indexes (support @>, ?, ?&, ?| operators)
CREATE INDEX idx2_employees ON cards USING gin ((emp_data->'tags'));
CREATE INDEX idx3_employees ON employees USING gin (emp_data);
```
PostgreSQL supports B-Tree, HASH, and GIN indexes for JSON. Without indexes, JSON filtering forces full table scans (steps into each document), hurting performance.

### Summary mapping

| Feature | Oracle | Aurora PostgreSQL |
|---|---|---|
| Return full JSON document | `SELECT emp_data FROM employees;` | `SELECT emp_data FROM employees;` |
| Return a specific element | `SELECT e.emp_data.address FROM employees e;` | `SELECT emp_data->>'address' from employees where emp_id = 1;` |
| Pattern match any field | `SELECT e.emp_data FROM employees e WHERE e.emp_data like '%pattern%';` | `SELECT * from (select jsonb_pretty(emp_data) as raw_data from employees) raw_jason where raw_data like '%1234%';` or `SELECT key, value FROM card, lateral jsonb_each_text(data) WHERE value LIKE '%pattern%';` |
| Pattern match specific (root) field | `SELECT e.emp_data.name FROM employees e WHERE e.data.active = 'true';` | `SELECT * FROM employees WHERE emp_data->>'active' = 'true';` |
| Define JSON column | CLOB column + `IS JSON` constraint | `CREATE TABLE json_docs ( id integer NOT NULL, data jsonb );` |

## Conversion notes
- Different paradigm/syntax — **application or driver rewrite required** (low feature compatibility, two stars).
- Oracle dot-notation queries must be rewritten to PostgreSQL operators (`->`, `->>`, `?`, `?|`, `?&`, `@>`).
- Prefer **JSONB** over JSON for performance; use **GIN** indexes for containment/key-existence queries.
- Enforce uniqueness/constraints via expression `CREATE UNIQUE INDEX` on extracted keys.
- Set database encoding to UTF8 for full JSON spec compliance.
