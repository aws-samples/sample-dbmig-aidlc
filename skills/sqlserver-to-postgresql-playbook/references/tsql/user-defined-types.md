# User-Defined Types

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.udt.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Scalar alias UDT→CREATE DOMAIN (verified NOT NULL/CHECK enforcement and the outer-join NULL caveat); removed Oracle 'CREATE OR REPLACE TYPE … AS OBJECT' syntax (fails on PG); CLR UDTs→ltree/PostGIS; TVP types→composite arrays/jsonb.

## SQL Server

User-defined types encapsulate custom data types and can add NULL constraints. All UDTs are based on existing system data types, improving readability. SQL Server also supports table-valued UDTs (to pass a set to a stored procedure) and CLR-associated types (and memory-optimized types since 2014). Custom rules bound to types are deprecated.

Syntax:

```sql
CREATE TYPE <type name> {
FROM <base type> [ NULL | NOT NULL ] | AS TABLE (<Table Definition>)}
```

Scalar UDT example:

```sql
CREATE TYPE ZipCode
FROM CHAR(5)
NOT NULL

CREATE TABLE UserLocations
(UserID INT NOT NULL PRIMARY KEY, ZipCode ZipCode);

INSERT INTO [UserLocations] ([UserID],[ZipCode]) VALUES (1, '94324');
-- NULL fails the NOT NULL UDT constraint
```

Table-valued type example:

```sql
CREATE TYPE OrderItems AS TABLE
(
  OrderID INT NOT NULL,
  Item VARCHAR(20) NOT NULL,
  Quantity SMALLINT NOT NULL,
  PRIMARY KEY(OrderID, Item)
);

CREATE PROCEDURE InsertOrderItems
@OrderItems AS OrderItems READONLY
AS
BEGIN
  INSERT INTO OrderItems(OrderID, Item, Quantity)
  SELECT OrderID, Item, Quantity FROM @OrderItems;
END
```

## PostgreSQL

PostgreSQL also uses `CREATE TYPE`. A UDT is owned by its creator (in a schema if specified). Supported kinds:
- **Composite types** — one or more named attributes; can be associated to a table.
- **Enumerated (enum) types** — static ordered set of values:
  ```sql
  CREATE TYPE PRODUCT_CATEGORT AS ENUM ('Hardware', 'Software', 'Document');
  ```
- **Range types** — a range of values:
  ```sql
  CREATE TYPE float8_range AS RANGE (subtype = float8, subtype_diff = float8mi);
  ```
- **Base types** — core system types implemented in a low-level language (C).
- **Array types** — columns as multidimensional arrays:
  ```sql
  CREATE TABLE COURSE_SCHEDULE (
    COURSE_ID NUMERIC PRIMARY KEY,
    COURSE_NAME VARCHAR(60),
    COURSE_SCHEDULES text[]);
  ```

Syntax (range and base type):

```sql
CREATE TYPE name AS RANGE (
  SUBTYPE = subtype
  [ , SUBTYPE_OPCLASS = subtype_operator_class ]
  [ , COLLATION = collation ]
  [ , CANONICAL = canonical_function ]
  [ , SUBTYPE_DIFF = subtype_diff_function ]
)
CREATE TYPE name (
  INPUT = input_function,
  OUTPUT = output_function
  [ , RECEIVE = receive_function ]
  ... )
```

Composite type examples:

```sql
CREATE TYPE EMP_PHONE_NUM AS (
  PHONE_NUM VARCHAR(11));

CREATE TABLE EMPLOYEES (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_PHONE EMP_PHONE_NUM NOT NULL);

INSERT INTO EMPLOYEES VALUES(1, ROW('111-222-333'));
SELECT a.EMP_ID, (a.EMP_PHONE).PHONE_NUM FROM EMPLOYEES a;
-- 1  111-222-333

CREATE TYPE EMP_ADDRESS AS (   -- the original showed Oracle's CREATE OR REPLACE TYPE … AS OBJECT, a syntax error in PostgreSQL
  STATE VARCHAR(2), CITY VARCHAR(20), STREET VARCHAR(20), ZIP_CODE NUMERIC);

CREATE TABLE EMPLOYEES (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_NAME VARCHAR(10) NOT NULL,
  EMP_ADDRESS EMP_ADDRESS NOT NULL);

INSERT INTO EMPLOYEES VALUES(1, 'John Smith', ('AL', 'Gulf Shores', '3033 Joyce Street', '36542'));
SELECT a.EMP_NAME, (a.EMP_ADDRESS).STATE, (a.EMP_ADDRESS).CITY,
  (a.EMP_ADDRESS).STREET, (a.EMP_ADDRESS).ZIP_CODE FROM EMPLOYEES a;
```

## SQL Server alias types → domains (verified on Aurora PostgreSQL 18.6)

```sql
-- CREATE TYPE ZipCode FROM CHAR(5) NOT NULL
CREATE DOMAIN zipcode AS char(5) NOT NULL;

CREATE TABLE userlocations (userid int PRIMARY KEY, zipcode zipcode);
INSERT INTO userlocations VALUES (1, '94324');   -- ok
INSERT INTO userlocations VALUES (2, NULL);      -- ERROR 23502: domain zipcode does not allow null values

-- deprecated sp_bindrule rules → a domain CHECK
CREATE DOMAIN zipcode5 AS varchar(5) CHECK (VALUE ~ '^[0-9]{5}$');
```

- A domain `NOT NULL` is weaker than a column `NOT NULL`: an outer join can still produce NULLs of the domain type (verified). For columns that must never be NULL, also put `NOT NULL` on the column.
- Domains are enforced on every assignment, including function parameters and PL/pgSQL variables of the domain type, which SQL Server alias types do not do for `NOT NULL`.
- `ALTER DOMAIN … ADD CONSTRAINT … NOT VALID` lets you add a rule without rechecking existing rows; validate later with `ALTER DOMAIN … VALIDATE CONSTRAINT`.
- Character base types follow the toolkit datatype map (`engines/sqlserver-to-postgresql/datatype-map.yaml`); `nchar`/`nvarchar` alias types become `char`/`varchar` domains.
- CLR UDTs (`hierarchyid`, `geometry`, `geography`, custom assemblies) are not alias types: `hierarchyid` → `ltree` (toolkit convention), spatial → PostGIS `geometry`/`geography`, custom CLR types → composite type or `jsonb` plus functions (see `common-language-runtime.md`).
- Memory-optimized table types have no equivalent; use a regular composite-type array or a temporary table.

## Conversion notes
- Both engines use `CREATE TYPE`; conversion is largely automatic.
- SQL Server scalar UDT (`FROM <base type> NOT NULL`) → PostgreSQL **`CREATE DOMAIN`** (not a composite type: a one-field composite changes how values are written and read).
- Table-valued types: SQL Server `AS TABLE` UDTs map to PostgreSQL composite types; table-valued parameters become `composite[]` (unpack with `unnest`) or `jsonb` (`jsonb_populate_recordset`), both verified in `stored-procedures.md`. Composite types cannot carry the TVP's `PRIMARY KEY`/`CHECK`; enforce them in the procedure or on the target table.
- Access composite attributes with `(column).attribute` syntax and construct with `ROW(...)`.
- PostgreSQL adds enum, range, and array types not present as UDTs in SQL Server.
