# JSON and XML for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.xml.html

**Conversion category:** Manual (Two star feature compatibility) — minimal XML support; extensive JSON support
**SCT automation:** Four star automation level

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

Two functions only: `ExtractValue` (XPath child CDATA, space-delimited on multiple matches) and `UpdateXML` (replace fragment by XPath; returns original if zero/multiple matches). `LOAD XML` is not supported in Aurora MySQL.

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

JSON columns (BINARY family) can't be indexed directly. Add a generated (computed/persisted) column extracting a JSON value and index that; the optimizer can then use it for JSON expressions.

## Conversion notes

- No XQuery support in Aurora MySQL — optionally convert XML data to JSON.
- XML: replace `XQUERY`/`XPATH`, `OPENXML`, `FOR XML` with the limited `ExtractValue`/`UpdateXML`.
- JSON: SQL Server `NVARCHAR`+functions → Aurora native `JSON` type + 25+ functions (richer than SQL Server). Map `JSON_VALUE`/`JSON_QUERY`→`JSON_EXTRACT`, `OPENJSON`/`FOR JSON` have no direct equivalents.
- Indexing JSON requires generated columns + explicit index (vs SQL Server PATH/VALUE/PROPERTY indexes).

| Feature | SQL Server | Aurora MySQL |
|---|---|---|
| Native semi-structured type | `XML` (with schema collections) | `JSON` |
| JSON functions | `ISJSON`, `JSON_VALUE`, `JSON_QUERY`, `JSON_MODIFY`, `OPENJSON`, `FOR JSON` | 25+ dedicated JSON functions |
| XML functions | `XQUERY`/`XPATH`, `OPENXML`, `FOR XML` | `ExtractValue`, `UpdateXML` |
| Indexes | Primary/secondary PATH/VALUE/PROPERTY | Generated columns + index; optimizer uses JSON expressions |
