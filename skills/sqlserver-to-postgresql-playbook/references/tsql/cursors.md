# Cursors

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.cursors.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Cursors

## SQL Server

Cursors provide row-by-row sequential access to result sets as an alternative to set-based operations. They support positioning (absolute/relative offsets), retrieving rows/blocks, modifying at the current position, and isolating concurrent modifications. Usable in scripts, stored procedures, and triggers.

Syntax:

```sql
DECLARE <Cursor Name>
CURSOR [LOCAL | GLOBAL]
  [FORWARD_ONLY | SCROLL]
  [STATIC | KEYSET | DYNAMIC | FAST_FORWARD]
  [ READ_ONLY | SCROLL_LOCKS | OPTIMISTIC]
  [TYPE_WARNING]
  FOR <SELECT statement>
  [ FOR UPDATE [ OF <Column List>]][;]

FETCH [NEXT | PRIOR | FIRST | LAST | ABSOLUTE <Value> | RELATIVE <Value>]
FROM <Cursor Name> INTO <Variable List>;
```

Example:

```sql
DECLARE MyCursor CURSOR FOR
  SELECT * FROM Table1 AS T1
    INNER JOIN Table2 AS T2 ON T1.Col1 = T2.Col1;
OPEN MyCursor;
DECLARE @VarCursor1 VARCHAR(20);
FETCH NEXT FROM MyCursor INTO @VarCursor1;
WHILE @@FETCH_STATUS = 0
BEGIN
  EXEC MyPRocessingProcedure @InputParameter = @VarCursor1;
  FETCH NEXT FROM product_cursor INTO @VarCursor1;
END
CLOSE MyCursor;
DEALLOCATE MyCursor;
```

## PostgreSQL

PL/pgSQL cursors iterate over rows. All cursor access uses cursor variables of type `refcursor`.

SQL Server `DECLARE..CURSOR` options with no PostgreSQL equivalent:

| SQL Server option | Use | PostgreSQL comment |
|---|---|---|
| `FORWARD_ONLY` | only `FETCH NEXT` | use `FOR LOOP` instead |
| `STATIC` | temp copy of data | use temp tables for small sets |
| `KEYSET` | fixed membership/order | N/A |
| `DYNAMIC` | reflects all data changes | Default in PostgreSQL |
| `FAST_FORWARD` | FORWARD_ONLY + READ_ONLY perf | N/A |
| `SCROLL_LOCKS` | positioned updates guaranteed | N/A |
| `OPTIMISTIC` | positioned update fails if row changed | N/A |
| `TYPE_WARNING` | warn on implicit type conversion | N/A |

**Declare:**

```sql
DECLARE c1 refcursor;                                   -- unbound
DECLARE c2 CURSOR FOR SELECT * FROM employees;          -- bound
DECLARE c3 CURSOR (var1 integer) FOR SELECT * FROM employees where id = var1;  -- parameterized
DECLARE c3 SCROLL CURSOR FOR SELECT id, name FROM employees;  -- backward-scrollable
```
- `SCROLL` allows backward fetch (may cost performance); `NO SCROLL` rejects backward fetch.
- Backward fetches not allowed with `FOR UPDATE`/`FOR SHARE`.

**Open:**

```sql
OPEN c1 FOR SELECT * FROM employees WHERE id = emp_id;
OPEN c1 FOR EXECUTE format('SELECT * FROM %I WHERE col1 = $1',tabname) USING keyvalue;
-- parameterized bound cursor:
OPEN c3(var1 := 42);
```

**Fetch:**

```sql
FETCH [ direction [ FROM | IN ] ] cursor_name
```

Directions: `NEXT`, `PRIOR`, `FIRST`, `LAST`, `ABSOLUTE count`, `RELATIVE count`, `FORWARD`/`FORWARD n`/`FORWARD ALL`, `BACKWARD`/`BACKWARD n`/`BACKWARD ALL`, `ALL`. Omitting direction = `NEXT`.

```sql
DO $$
DECLARE
  c3 CURSOR FOR SELECT * FROM employees;
  rowvar employees%ROWTYPE;
BEGIN
  OPEN c3;
  FETCH c3 INTO rowvar;
END$$;
```

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Cursor options | `[FORWARD_ONLY\|SCROLL][STATIC\|KEYSET\|DYNAMIC\|FAST_FORWARD][READ_ONLY\|SCROLL_LOCKS\|OPTIMISTIC]` | `[BINARY][INSENSITIVE][[NO]SCROLL]CURSOR[{WITH\|WITHOUT}HOLD]` |
| Updateable cursors | `DECLARE CURSOR... FOR UPDATE` | `DECLARE cur_name CURSOR... FOR UPDATE` |
| Cursor declaration | `DECLARE CURSOR` | `DECLARE cur_name CURSOR` |
| Cursor open | `OPEN` | `OPEN` |
| Cursor fetch | `FETCH NEXT\|PRIOR\|FIRST\|LAST\|ABSOLUTE\|RELATIVE` | `FETCH [direction [FROM\|IN]] cursor_name` |
| Cursor close | `CLOSE` | `CLOSE` |
| Cursor deallocate | `DEALLOCATE` | Same effect as CLOSE (not required) |
| Cursor end condition | `@@FETCH_STATUS` system variable | Not supported |

## Conversion notes
- Most cursor operations map directly (`DECLARE`/`OPEN`/`FETCH`/`CLOSE`).
- `@@FETCH_STATUS` has no equivalent — restructure loops using PL/pgSQL `FOR` loops or check `FOUND`/`NOT FOUND`.
- `DEALLOCATE` is unnecessary in PostgreSQL (`CLOSE` is sufficient).
- DYNAMIC behavior is the PostgreSQL default; STATIC/KEYSET/FAST_FORWARD/SCROLL_LOCKS/OPTIMISTIC/TYPE_WARNING have no equivalents — re-design as needed.
- Prefer `FOR LOOP` over explicit cursors where possible for simpler, idiomatic code.
