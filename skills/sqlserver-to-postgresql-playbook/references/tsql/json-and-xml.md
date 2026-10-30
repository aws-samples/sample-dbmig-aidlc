# JSON and XML

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.json.html

**Conversion category:** Automatic (four-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: XML

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Added SQL/JSON standard mappings (IS JSON, JSON_VALUE, JSON_QUERY, JSON_EXISTS, JSON_TABLE, JSON_OBJECT/ARRAYAGG; all verified), JSON_MODIFY→jsonb_set/jsonb_set_lax, FOR XML→xmlagg (verified); corrected the XMLNAMESPACES(DEFAULT) advice (fails on 18.6) and a CREATE INDEX typo; XMLVALIDATE not implemented.

## SQL Server

SQL Server provides native T-SQL support for both JSON and XML semi-structured data.

**XML** — extensive native support:
- *Native XML data type* (BLOB structure preserving XML Infoset; allows schema validation; white space removed and object order may change).
- *Annotated Schema (AXSD)* distributes XML across tables (hierarchy maintained, element order not).
- CLOB/BLOB (`VARCHAR(MAX)`, `VARBINARY(MAX)`) to store original text.
- *XML indexes*: PRIMARY and SECONDARY (`PATH`, `VALUE`, `PROPERTY`).
- *XQuery* (subset of W3C spec):

```sql
DECLARE @XMLVar XML = '<Root><Data>My XML Data</Data></Root>';
SELECT @XMLVar.query('/Root/Data');
-- Result: <Data>My XML Data</Data>
```

**JSON** — no dedicated type; stored in `NVARCHAR`. Functions: `ISJSON`, `JSON_VALUE` (scalar), `JSON_QUERY` (object/array), `JSON_MODIFY`, `OPENJSON` (JSON → set). `FOR JSON` clause converts a tabular set to JSON.

```sql
DECLARE @JSONVar NVARCHAR(MAX);
SET @JSONVar = '{"Data":{"Person":[{"Name":"John"},{"Name":"Jane"},{"Name":"Maria"}]}}';
SELECT JSON_QUERY(@JSONVar, '$.Data');
```

## PostgreSQL

Native JSON support via `JSON` and `JSONB` types:
- `JSON` stores exact text (re-parsed each use; preserves white space, key order, duplicates).
- `JSONB` stores decomposed binary (slightly slower input, much faster processing; no white space, no key order, dedupes keys keeping last). Most apps use `JSONB`.

For full JSON spec compliance, database encoding must be UTF8. From PostgreSQL 10, JSON/JSONB are compatible with full-text search.

JSON query examples (different syntax than SQL Server):

```sql
SELECT emp_data FROM employees WHERE emp_id = 1;

-- has a key named address:
SELECT emp_data FROM employees WHERE emp_data ? 'address';

-- has address OR hobbies key:
SELECT * FROM employees WHERE emp_data ?| array['address', 'hobbies'];

-- has both keys:
SELECT * FROM employees WHERE emp_data ?& array['a', 'b'];

-- nested value (home within phone numbers):
SELECT emp_data ->'phone numbers'->>'home' FROM employees;

-- equality and LIKE on a key:
SELECT * FROM employees WHERE emp_data->>'address' = '1234 First Street, Capital City';
SELECT * FROM employees WHERE emp_data->>'address' like '%Capital City%';

-- remove keys (multiple keys: PostgreSQL 10+):
select '{"id":132, "fname":"John", "salary":999999, "bank_account":1234}'::jsonb - '{salary,bank_account}'::text[];
```

**Indexing / constraints on JSONB:**

```sql
-- unique constraint on a JSON key:
CREATE UNIQUE INDEX employee_address_uq ON employees( (emp_data->>'address') );

-- expression index on a key:
CREATE INDEX idx1_employees ON employees ((emp_data->>'address'));

-- GIN index on a key or whole column (operators: @>, ?, ?&, ?|):
CREATE INDEX idx2_employees ON cards USING gin ((emp_data->'tags'));
CREATE INDEX idx3_employees ON employees USING gin (emp_data);
```

PostgreSQL supports B-tree, hash, and GIN for JSON. Without indexes, queries cause full table scans.

**XML** — native `xml` type (type-checked on insert), stores documents or content fragments; `IS DOCUMENT` tests which.

```sql
CREATE TABLE test (a xml);
insert into test values (XMLPARSE (DOCUMENT '<?xml version="1.0"?><Series><title>Simpsons</title><chapter>...</chapter></Series>'));
insert into test values (XMLPARSE (CONTENT 'note<tag>value</tag><tag>value</tag>'));
select * from test where a IS DOCUMENT;
```

XML → rows via `XMLTABLE` (PostgreSQL 10+):

```sql
SELECT xmltable.*
  FROM xmldata_sample,
    XMLTABLE('//ROWS/ROW'
      PASSING data
      COLUMNS id int PATH '@id',
        ordinality FOR ORDINALITY,
        "EMP_NAME" text,
        "EMP_ID" text PATH 'EMP_ID',
        SALARY_USD float PATH 'SALARY[@unit = "dollars"]',
        MANAGER_NAME text PATH 'MANAGER_NAME' DEFAULT 'not specified');
```

## Converting `xml.value(...)` with namespaces (from a real run)

AdventureWorks views (`Sales.vStoreWithDemographics`, `Sales.vPersonDemographics`)
extract scalars from a namespaced XML column with SQL Server's
`col.value('declare default element namespace "<uri>"; (/Root/Node)[1]', 'type')`.
The PostgreSQL equivalent is `xpath(text-node, col, ns-array)` taking the first
array element and casting:

```sql
-- SQL Server
s.Demographics.value(
  'declare default element namespace "http://.../StoreSurvey";
   (/StoreSurvey/AnnualSales)[1]', 'money') AS AnnualSales

-- PostgreSQL  (bind the default namespace to a prefix, e.g. x)
(xpath('/x:StoreSurvey/x:AnnualSales/text()', s.demographics,
       ARRAY[ARRAY['x','http://.../StoreSurvey']]))[1]::text::numeric(19,4) AS annualsales
```

Patterns that recur:
- **Always declare the namespace** as a prefix in the third `xpath` argument and use
  that prefix on every step (`/x:Root/x:Node`); SQL Server's *default* element
  namespace has no unprefixed PostgreSQL equivalent.
- **Scalar extraction**: append `/text()`, take `(...)[1]`, cast `::text` then to the
  target type (`::numeric`, `::int`). Missing nodes yield `NULL` (empty array).
- **Dates** stored as `2001-07-22Z`: `replace((xpath(...))[1]::text,'Z','')::timestamp`
  (mirrors the source `CONVERT(datetime, REPLACE(v,'Z',''),101)`).
- **bit flags** (`0`/`1` text): `(xpath(...))[1]::text::int::boolean`.
- For many rows / repeated shredding prefer **`XMLTABLE`** (above) over many per-column
  `xpath()` calls, with a **prefixed** namespace:
  `XMLTABLE(XMLNAMESPACES('<uri>' AS x), '/x:Root' PASSING col COLUMNS v numeric PATH 'x:Node')`.
  `XMLNAMESPACES(DEFAULT '<uri>')` fails on PostgreSQL ("DEFAULT namespace is not supported",
  verified on Aurora PostgreSQL 18.6).

## SQL/JSON standard functions (PostgreSQL 16/17, verified on Aurora PostgreSQL 18.6)

PostgreSQL now has the same SQL-standard functions SQL Server uses, so most JSON code converts nearly unchanged:

| SQL Server | PostgreSQL 18 | Notes |
|---|---|---|
| `ISJSON(x)` (returns 1/0) | `x IS JSON` / `IS JSON OBJECT` / `IS JSON ARRAY` | returns boolean; wrap in `CASE` or `::int` if callers expect 1/0 |
| `JSON_VALUE(x, '$.a.b')` | `JSON_VALUE(x, '$.a.b' [RETURNING numeric])` | default lax mode returns NULL for a missing path, as in SQL Server |
| `JSON_VALUE(x, 'strict $.b')` | `JSON_VALUE(x, 'strict $.b' ERROR ON ERROR)` | without `ERROR ON ERROR` PostgreSQL returns NULL even in strict mode |
| `JSON_QUERY(x, '$.Data')` | `JSON_QUERY(x, '$.Data')` | |
| `OPENJSON(x, '$.P') WITH (Name nvarchar(50) '$.Name')` | `JSON_TABLE(x, '$.P[*]' COLUMNS (name text PATH '$.Name'))` | `FOR ORDINALITY` replaces the `[key]` column |
| `OPENJSON(x)` (no `WITH`, key/value/type) | `jsonb_each(x)` / `jsonb_array_elements(x)` | |
| `JSON_MODIFY(x, '$.a.b', v)` | `jsonb_set(x, '{a,b}', to_jsonb(v))`; append → `jsonb_insert`; set to NULL deletes in SQL Server → `jsonb_set_lax(…, 'delete_key')` or `x #- '{a,b}'` | |
| `FOR JSON PATH` | `json_agg(t ORDER BY …)` / `JSON_ARRAYAGG(JSON_OBJECT('k': v) ORDER BY …)` | `FOR JSON … WITHOUT_ARRAY_WRAPPER` → `row_to_json(t)` |
| `JSON_OBJECT` / `JSON_ARRAY` (SQL Server 2022) | `JSON_OBJECT('a': 1)` / `JSON_ARRAY(…)` | `JSON_ARRAY` skips NULLs by default (`ABSENT ON NULL`); add `NULL ON NULL` if needed |
| `JSON_PATH_EXISTS` | `JSON_EXISTS(x, '$.a.b')` | |

## FOR XML (verified on 18.6)

`FOR XML PATH('Order'), ROOT('Orders')` → `xmlelement` + `xmlagg` + `xmlforest`/`xmlattributes`, not `string_agg` (which does no escaping):

```sql
SELECT xmlelement(name "Orders",
         xmlagg(xmlelement(name "Order", xmlattributes(id AS "ID"), xmlforest(name AS "Name"))
                ORDER BY id))
FROM orders;
-- <Orders><Order ID="1"><Name>a</Name></Order>…</Orders>
```

The `FOR XML PATH(''), TYPE).value('.', 'nvarchar(max)')` string-concatenation idiom → `string_agg(col, ',' ORDER BY …)`.

XML schema collections (typed `xml`) have no equivalent: PostgreSQL's `XMLVALIDATE` is not implemented, so validate in the application or with a trigger that checks structure via `xpath_exists`. XML indexes have no equivalent; index extracted values with an expression index on `((xpath('/x:a/text()', col, ns))[1]::text)` or shred into columns.

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| XML and JSON native data types | XML with schema collections | JSON / JSONB (and XML) |
| JSON functions | `ISJSON`, `JSON_VALUE`, `JSON_QUERY`, `JSON_MODIFY`, `OPENJSON`, `FOR JSON` | `IS JSON`, `JSON_VALUE`, `JSON_QUERY`, `JSON_EXISTS`, `JSON_TABLE` (PG 16/17) plus `jsonb_*` functions and operators |
| XML functions | `XQUERY`/`XPATH`, `OPENXML`, `FOR XML` | `xpath`, `XMLTABLE`, `xmlelement`/`xmlagg`/`xmlforest`; **no `FOR XML` clause or XQuery `.modify()`** |
| XML and JSON indexes | Primary/Secondary PATH, VALUE, PROPERTY | Supported (B-tree, hash, GIN) |

## Conversion notes
- Map SQL Server JSON-in-`NVARCHAR` to native `JSONB` (preferred) for performance and indexing.
- Prefer the SQL-standard `JSON_VALUE`/`JSON_QUERY`/`JSON_TABLE`/`IS JSON` (same names as SQL Server) over the `->`/`->>` operators when converting T-SQL; use the operators and `@>` where a GIN index must serve the predicate.
- **No `FOR XML`** — rebuild XML output with `xmlelement`/`xmlagg`/`xmlforest`; `FOR JSON` → `json_agg`/`JSON_ARRAYAGG`/`row_to_json`.
- `OPENJSON` → `JSON_TABLE` (or `jsonb_to_recordset`); `OPENXML` / `.nodes()` → `XMLTABLE` with prefixed namespaces.
- `.value('(/a/b)[1]', 'int')` → `(xpath('/a/b/text()', col))[1]::text::int`; `.exist()` → `xpath_exists`; `.modify()` (XML DML) has no equivalent: rebuild the document or store as JSONB.
- Use GIN indexes for JSONB containment/key queries (`@>`, `?`, `?&`, `?|`).
- Set database encoding to UTF8 for full JSON compliance.
