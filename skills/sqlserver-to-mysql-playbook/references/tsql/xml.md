# JSON and XML for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.xml.html

**Conversion category:** Manual (Two star feature compatibility) — minimal XML support; extensive JSON support
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected LOAD XML (LOAD XML FROM S3 exists) and 'no OPENJSON/FOR JSON equivalent' (JSON_TABLE / JSON_ARRAYAGG on MySQL 8 — verified); ExtractValue namespace/malformed behavior (verified); multi-valued indexes; FOR XML PATH concatenation.

## SQL Server

Provides native support for XML and JSON via T-SQL.

### XML

- Native `XML` data type (BLOB preserving XML infoset; supports schema validation), annotated schema (AXSD) distribution, or CLOB/BLOB (`VARCHAR(MAX)`/`VARBINARY(MAX)`).
- XML indexes: `PRIMARY` and `SECONDARY` (`PATH`, `VALUE`, `PROPERTY`) on native XML columns.
- XQuery (subset of W3C spec):

```sql
DECLARE @XMLVar XML = '<Root><Data>My XML Data</Data></Root>';
SELECT @XMLVar.query('/Root/Data');
-- Result: <Data>My XML Data</Data>

CREATE TABLE MyTable
(
    XMLIdentifier INT NOT NULL PRIMARY KEY,
    XMLDocument XML NULL
);
```

### JSON

No dedicated JSON type — store in `NVARCHAR`. Functions: `ISJSON`, `JSON_VALUE` (scalar), `JSON_QUERY` (object/array), `JSON_MODIFY`, `OPENJSON` (JSON→set), and `FOR JSON` (set→JSON).

```sql
DECLARE @JSONVar NVARCHAR(MAX);
SET @JSONVar = '{"Data":{"Person":[{"Name":"John"},{"Name":"Jane"},{"Name":"Maria"}]}}';
SELECT JSON_QUERY(@JSONVar, '$.Data');
```

## MySQL

Opposite of SQL Server: minimal XML support, but a **native JSON data type** plus 25+ JSON functions.

### XML

Two functions only: `ExtractValue` (XPath child CDATA, space-delimited on multiple matches) and `UpdateXML` (replace fragment by XPath; returns original if zero/multiple matches). *(corrected)* XML files can be loaded with **`LOAD XML FROM S3`** (Aurora). Verified on 3.13 and 8.4.8: `ExtractValue` supports attributes and `count()`, **ignores namespaces**, and returns **NULL for malformed XML** (with a warning, not an error).

```sql
SELECT ExtractValue('<Root><Person>John</Person><Person>Jim</Person></Root>', '/Root/Person');
-- Results: John Jim

SELECT UpdateXML('<Root><Person>John</Person><Person>Jim</Person></Root>', '/Root', '<Person>Jack</Person>');
-- Results: <Person>Jack</Person>
```

### JSON

Native `JSON` type (validates on insert; optimized binary storage for fast access):

```sql
CREATE TABLE JSONTable (DocumentIdentifier INT NOT NULL PRIMARY KEY, JSONDocument JSON);
```

25+ functions, including:
- Construct: `JSON_ARRAY`, `JSON_OBJECT`, `JSON_QUOTE`
- Query/search: `JSON_CONTAINS`, `JSON_CONTAINS_PATH`, `JSON_EXTRACT`, `JSON_KEYS`, `JSON_SEARCH`
- Modify: `JSON_INSERT`, `JSON_REMOVE`, `JSON_REPLACE`, `JSON_SET`, `JSON_ARRAY_INSERT`
- Utility (5.7.22+): `JSON_PRETTY`, `JSON_STORAGE_SIZE`, `JSON_STORAGE_FREE`
- Aggregation (MySQL 8): `JSON_ARRAYAGG`, `JSON_OBJECTAGG`
- Validation (MySQL 8.0.17): `JSON_SCHEMA_VALID`, `JSON_SCHEMA_VALIDATION_REPORT`

```sql
SELECT JSON_OBJECT('Person', 'John', 'Country', 'USA');
-- {"Person": "John", "Country": "USA"}

SELECT JSON_EXTRACT('["Mary", "Paul", ["Jim", "Ryan"]]', '$[1]');  -- "Paul"
SELECT JSON_SEARCH('["Mary", "Paul", ["Jim", "Ryan"]]', 'one', 'Paul');  -- "$[1]"
SELECT JSON_ARRAY_INSERT('["Mary", "Paul", "Jim"]', '$[1]', 'Jack');
-- ["Mary", "Jack", "Paul", "Jim"]
```

### JSON indexes

JSON columns can't be indexed directly. Options (all verified on 3.13 and 8.4.8): a generated column (`VIRTUAL` or `STORED`) extracting a value plus an index; a functional index; or a **multi-valued index** on a JSON array (`INDEX ((CAST(d->'$.tags' AS CHAR(20) ARRAY)))`, used by `MEMBER OF` / `JSON_CONTAINS` / `JSON_OVERLAPS`).

## Conversion notes

- No XQuery support in Aurora MySQL — optionally convert XML data to JSON.
- XML: replace `XQUERY`/`XPATH`, `OPENXML`, `FOR XML` with the limited `ExtractValue`/`UpdateXML`.
- JSON: SQL Server `NVARCHAR`+functions → Aurora native `JSON` type. *(corrected for MySQL 8)* direct mappings exist (verified): `ISJSON` → `JSON_VALID`; `JSON_VALUE` → `JSON_VALUE` (8.0.21+, with `RETURNING type`); `JSON_QUERY` → `JSON_EXTRACT` / `->`; `JSON_MODIFY` → `JSON_SET` / `JSON_REPLACE` / `JSON_REMOVE`; **`OPENJSON … WITH (…)` → `JSON_TABLE(…, '$[*]' COLUMNS (…))`**; **`FOR JSON PATH` → `JSON_ARRAYAGG(JSON_OBJECT(…))`**. Invalid JSON is rejected on insert into a `JSON` column (error 3140).
- `FOR XML PATH('')` used for string concatenation → `GROUP_CONCAT(… SEPARATOR …)`; `FOR XML PATH('row')` producing XML → `CONCAT`/`GROUP_CONCAT` with manual escaping, or emit JSON instead.
- `xml.value('(/a/b)[1]','int')` → `CAST(ExtractValue(x, '/a/b[1]') AS SIGNED)`; `xml.nodes()` shredding → no equivalent (convert the documents to JSON and use `JSON_TABLE`); `xml.modify()` → `UpdateXML` for single-node replacement only.
- Toolkit datatype map: `XML` → `LONGTEXT`.
- Indexing JSON requires generated columns + explicit index (vs SQL Server PATH/VALUE/PROPERTY indexes).

| Feature | SQL Server | Aurora MySQL |
|---|---|---|
| Native semi-structured type | `XML` (with schema collections) | `JSON` |
| JSON functions | `ISJSON`, `JSON_VALUE`, `JSON_QUERY`, `JSON_MODIFY`, `OPENJSON`, `FOR JSON` | `JSON_VALID`, `JSON_VALUE`, `JSON_EXTRACT`, `JSON_SET`, `JSON_TABLE`, `JSON_ARRAYAGG`/`JSON_OBJECT` |
| XML functions | `XQUERY`/`XPATH`, `OPENXML`, `FOR XML` | `ExtractValue`, `UpdateXML` |
| Indexes | Primary/secondary PATH/VALUE/PROPERTY | Generated columns + index; optimizer uses JSON expressions |
