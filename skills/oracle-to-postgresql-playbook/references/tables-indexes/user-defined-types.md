# User-Defined Types

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.udt.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** User-Defined Types action code index. PostgreSQL doesn't support the `FORALL` statement, the `DEFAULT` option, or collection-type constructors.

## Oracle
Oracle UDTs are `OBJECT TYPES`, managed via PL/SQL and built on/extending built-in types. `CREATE TYPE` supports: object types, varying array (varray) types, nested table types, incomplete types, and SQLJ object types (Java class mapped to a SQL UDT).

```sql
CREATE OR REPLACE TYPE EMP_PHONE_NUM AS OBJECT (
  PHONE_NUM VARCHAR2(11));

CREATE TABLE EMPLOYEES (
  EMP_ID NUMBER PRIMARY KEY,
  EMP_PHONE EMP_PHONE_NUM NOT NULL);

INSERT INTO EMPLOYEES VALUES(1, EMP_PHONE_NUM('111-222-333'));
SELECT a.EMP_ID, a.EMP_PHONE.PHONE_NUM FROM EMPLOYEES a;
```

Object type as a collection of attributes:
```sql
CREATE OR REPLACE TYPE EMP_ADDRESS AS OBJECT (
  STATE VARCHAR2(2), CITY VARCHAR2(20),
  STREET VARCHAR2(20), ZIP_CODE NUMBER);

CREATE TABLE EMPLOYEES (
  EMP_ID NUMBER PRIMARY KEY,
  EMP_NAME VARCHAR2(10) NOT NULL,
  EMP_ADDRESS EMP_ADDRESS NOT NULL);

INSERT INTO EMPLOYEES VALUES(1, 'John Smith',
  EMP_ADDRESS('AL', 'Gulf Shores', '3033 Joyce Street', '36542'));
SELECT a.EMP_ID, a.EMP_NAME, a.EMP_ADDRESS.STATE, a.EMP_ADDRESS.CITY,
  a.EMP_ADDRESS.STREET, a.EMP_ADDRESS.ZIP_CODE FROM EMPLOYEES a;
```

## PostgreSQL
PostgreSQL also uses `CREATE TYPE`. A UDT is owned by its creator (and created in a schema if specified). Supported kinds:
- **Composite** — one or more named attributes; can be standalone or associated with a table.
- **Enumerated (enum)** — static ordered set of values:
  ```sql
  CREATE TYPE PRODUCT_CATEGORT AS ENUM ('Hardware', 'Software', 'Document');
  ```
- **Range** — a range of values:
  ```sql
  CREATE TYPE float8_range AS RANGE (subtype = float8, subtype_diff = float8mi);
  ```
- **Base** — system core/abstract types, implemented in a low-level language like C.
- **Array** — columns as multidimensional arrays of built-in/UDT/enum/composite types:
  ```sql
  CREATE TABLE COURSE_SCHEDULE (
    COURSE_ID NUMERIC PRIMARY KEY,
    COURSE_NAME VARCHAR(60),
    COURSE_SCHEDULES text[]);
  ```

**CREATE TYPE synopsis:**
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
  [ , SEND = send_function ]
  [ , TYPMOD_IN = type_modifier_input_function ]
  [ , TYPMOD_OUT = type_modifier_output_function ]
  [ , ANALYZE = analyze_function ]
  [ , INTERNALLENGTH = { internallength | VARIABLE } ]
  [ , PASSEDBYVALUE ]
  [ , ALIGNMENT = alignment ]
  [ , STORAGE = storage ]
  [ , LIKE = like_type ]
  [ , CATEGORY = category ]
  [ , PREFERRED = preferred ]
  [ , DEFAULT = default ]
  [ , ELEMENT = element ]
  [ , DELIMITER = delimiter ]
  [ , COLLATABLE = collatable ]
)
```

Differences from Oracle `CREATE TYPE`:
- PostgreSQL does **not** support `CREATE OR REPLACE TYPE`.
- PostgreSQL does **not** accept `AS OBJECT`.

Composite type equivalent of the phone example (note `ROW(...)` on insert, parenthesized attribute access):
```sql
CREATE TYPE EMP_PHONE_NUM AS (PHONE_NUM VARCHAR(11));

CREATE TABLE EMPLOYEES (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_PHONE EMP_PHONE_NUM NOT NULL);

INSERT INTO EMPLOYEES VALUES(1, ROW('111-222-333'));
SELECT a.EMP_ID, (a.EMP_PHONE).PHONE_NUM FROM EMPLOYEES a;
```

## Conversion notes
- Replace Oracle `CREATE OR REPLACE TYPE ... AS OBJECT (...)` with PostgreSQL `CREATE TYPE ... AS (...)` (composite). Drop `OR REPLACE` and `AS OBJECT`.
- Constructor calls (e.g. `EMP_PHONE_NUM('...')`) become `ROW(...)`; attribute access requires parentheses: `(col).attr`.
- PostgreSQL lacks collection-type constructors, the `FORALL` statement, and the `DEFAULT` option for types.
- Oracle varray/nested-table collection types map best to PostgreSQL **array** types or composite types depending on use.
