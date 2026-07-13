# Cursors

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.cursors.html

**Conversion category:** Assisted (Four-star feature compatibility, three-star automation; minor syntax differences require some rewrite)
**SCT automation:** Three-star automation level; SCT action code index → Cursors

Key gaps: `TYPE … IS REF CURSOR` is not supported by PostgreSQL; `%ISOPEN`, `%BULK_EXCEPTIONS`, `%BULK_ROWCOUNT` are not supported.

## Oracle

PL/SQL cursors are pointers over result sets. Two types:
- **Implicit cursors** — auto-managed by PL/SQL for each `SELECT`/DML (a.k.a. SQL cursors).
- **Explicit cursors** — user-declared/named, associated with a query.

Explicit cursor (fetch into scalars, terminate on `%NOTFOUND`):

```sql
DECLARE
  CURSOR c1 IS
    SELECT last_name, job_id FROM employees
    WHERE REGEXP_LIKE (job_id, 'S[HT]_CLERK')
    ORDER BY last_name;
  v_lastname employees.last_name%TYPE;
  v_jobid employees.job_id%TYPE;
BEGIN
  OPEN c1;
  LOOP
    FETCH c1 INTO v_lastname, v_jobid;
    EXIT WHEN c1%NOTFOUND;
  END LOOP;
  CLOSE c1;
END;
```

Implicit cursor via FOR loop:

```sql
BEGIN
  FOR item IN
    (SELECT last_name, job_id FROM employees WHERE job_id LIKE '%MANAGER%'
     AND manager_id > 400 ORDER BY last_name) LOOP
    DBMS_OUTPUT.PUT_LINE('Name = ' || item.last_name || ', Job = ' || item.job_id);
  END LOOP;
END;
/
```

## PostgreSQL

PL/pgSQL cursors are accessed through cursor variables of type `refcursor`.

### DECLARE

```sql
DECLARE c1 refcursor;                                  -- unbound
DECLARE c2 CURSOR FOR SELECT * FROM employees;         -- bound (FOR; IS works for Oracle compat)
DECLARE c3 CURSOR (var1 integer) FOR SELECT * FROM employees where id = var1;  -- parameterized
DECLARE c3 SCROLL CURSOR FOR SELECT id, name FROM employees;  -- backward-scrollable
```
- `SCROLL` allows backward fetches (may hurt performance); `NO SCROLL` rejects them.
- Backward fetches not allowed with `FOR UPDATE`/`FOR SHARE`.

### OPEN

```sql
OPEN c1 FOR SELECT * FROM employees WHERE id = emp_id;
OPEN c1 FOR EXECUTE format('SELECT * FROM %I WHERE col1 = $1', tabname) USING keyvalue;

-- parameterized bound cursor
DO $$
DECLARE c3 CURSOR (var1 integer) FOR SELECT * FROM employees where id = var1;
BEGIN
  OPEN c3(var1 := 42);
END$$;
```

### FETCH

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
Direction clause supported: `NEXT` (default), `PRIOR`, `FIRST`, `LAST`, `ABSOLUTE count`, `RELATIVE count`, `FORWARD`, `BACKWARD`:

```sql
FETCH LAST FROM c3 INTO emp_id, emp_name;
```

### CLOSE / iterate

```sql
DO $$
DECLARE
  c3 CURSOR FOR SELECT * FROM employees;
  rowvar employees%ROWTYPE;
BEGIN
  OPEN c3;
  LOOP
    FETCH FROM c3 INTO rowvar;
    EXIT WHEN NOT FOUND;
  END LOOP;
  CLOSE c3;
END$$;
```

### MOVE (reposition without fetching)

```sql
MOVE LAST FROM c3;
MOVE RELATIVE -2 FROM c3;
MOVE FORWARD 2 FROM c3;
```

### UPDATE/DELETE WHERE CURRENT OF

```sql
UPDATE employee SET salary = salary*1.2 WHERE CURRENT OF c3;
```

### Implicit cursor (FOR loop)

```sql
DO $$
DECLARE item RECORD;
BEGIN
  FOR item IN (
    SELECT last_name, job_id FROM employees
    WHERE job_id LIKE '%MANAGER%' AND manager_id > 400 ORDER BY last_name
  )
  LOOP
    RAISE NOTICE 'Name = %, Job=%', item.last_name, item.job_id;
  END LOOP;
END $$;
```

## Summary — attribute/action mapping

| Action | Oracle PL/SQL | PostgreSQL PL/pgSQL |
|---|---|---|
| Declare bound cursor | `CURSOR c1 IS SELECT …` | `c2 CURSOR FOR SELECT …` |
| Open | `OPEN c1;` | `OPEN c2;` |
| Fetch into record | `FETCH c1 INTO rowvar;` | `FETCH c2 INTO rowvar;` |
| Fetch into scalars | `FETCH c1 INTO emp_id, emp_name, salary;` | same |
| Declare with variables | `CURSOR c1 (key NUMBER) IS …` | `C2 CURSOR (key integer) FOR …` |
| Open with variables | `OPEN c1(2);` | `OPEN c2(2);` or `OPEN c2(key := 2);` |
| Exit on no data | `EXIT WHEN c1%NOTFOUND;` | `EXIT WHEN NOT FOUND;` |
| Has rows remaining | `%FOUND` | `FOUND` |
| Rows affected (bulk) | `%BULK_ROWCOUNT` | Not supported; use `GET DIAGNOSTICS integer_var = ROW_COUNT;` per DML, store in array |
| Which DML failed | `%BULK_EXCEPTIONS` | N/A |
| Is cursor open | `%ISOPEN` | N/A |
| No rows remaining | `%NOTFOUND` | `NOT FOUND` |
| Rows affected | `%ROWCOUNT` | `GET DIAGNOSTICS integer_var = ROW_COUNT;` |

## Conversion notes

- Cursor variables are always `refcursor` in PL/pgSQL. `TYPE … IS REF CURSOR` (Oracle strongly-typed ref cursors) has no PG equivalent — redesign.
- Replace cursor attributes: `c%NOTFOUND`/`c%FOUND` → `NOT FOUND`/`FOUND` (the special `FOUND` variable, not cursor-qualified).
- No `%ISOPEN`, `%BULK_ROWCOUNT`, `%BULK_EXCEPTIONS` — use `GET DIAGNOSTICS … = ROW_COUNT` and arrays.
- PG adds `MOVE`, direction clauses, and `OPEN … FOR EXECUTE format(...)` for dynamic cursors.
- `WHERE CURRENT OF` is supported for positioned UPDATE/DELETE.
