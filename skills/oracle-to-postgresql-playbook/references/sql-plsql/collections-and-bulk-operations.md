# Collections and Bulk Operations (Oracle collections → PostgreSQL)

> Source: field notes from production Oracle 19c → Aurora PostgreSQL migrations
> (rail-ticketing schema: 45 Oracle types, 261 functions, 66 procedures).
> Complements the AWS playbook, which covers UDT **declarations** but not their
> **use inside PL/SQL**.

**Conversion category:** **Manual** — this is where the genuinely hard work is. The
type *declaration* is mechanical (see
[`../tables-indexes/user-defined-types.md`](../tables-indexes/user-defined-types.md));
the *code that consumes* collections usually needs redesign, not translation.

**Why it matters:** in the source migration, one mapping rule
(`TABLE OF <object>` → `RETURNS SETOF`) unblocked **38 functions**, the
collection-accumulation rewrite covered **14 large functions**, and one PostgreSQL
limitation (no arrays of anonymous records) blocked **two ~900-line functions**
outright until they were restructured.

---

## 1. Declaration mappings

| Oracle | PostgreSQL | Notes |
|---|---|---|
| `TYPE t IS OBJECT (a NUMBER, b VARCHAR2(10))` | `CREATE TYPE t AS (a numeric, b varchar(10))` | drop `OR REPLACE` and `AS OBJECT` |
| `TYPE tab IS TABLE OF <object_type>` | **no type** — the *function* returns `SETOF <object_type>` | see §2 |
| `TYPE arr IS TABLE OF <scalar>` | `CREATE DOMAIN arr AS <scalar>[]` | see §3 |
| `TYPE arr IS VARRAY(n) OF <scalar>` | `CREATE DOMAIN arr AS <scalar>[]` | the bound `n` is not enforced |
| `TYPE t IS TABLE OF x INDEX BY PLS_INTEGER` | no equivalent | associative array — see §6 |
| `SYS_REFCURSOR` | `refcursor` | see §7 |

Skip `MEMBER` / `STATIC` / `CONSTRUCTOR` / `MAP` / `ORDER` method declarations —
PostgreSQL composite types hold no methods. If a method carries logic, promote it to a
standalone function.

**Build a lookup table during type conversion** mapping each Oracle collection type to
`(kind, element_type)`, then reuse it for return types, parameter types **and** variable
declarations. Converting the declaration but missing a parameter that uses the same type
produces a confusing signature mismatch later.

---

## 2. `TABLE OF <object>` → a set-returning function

Do **not** try to materialise a nested table of objects as a PostgreSQL type.

```sql
-- Oracle:  TYPE t_avail IS TABLE OF type_avail;
FUNCTION get_avail(p_id NUMBER) RETURN t_avail;

-- PostgreSQL
CREATE FUNCTION get_avail(p_id numeric) RETURNS SETOF type_avail ...
```

`RETURNS TABLE(col type, ...)` is equally valid and often clearer for callers, because it
names the output columns. Prefer it when the Oracle object type exists *only* to shape a
function's result; keep `SETOF <composite>` when the type is shared or stored in a column.

Callers change too: `SELECT * FROM TABLE(get_avail(1))` → `SELECT * FROM get_avail(1)`.

---

## 3. Scalar collections → an array domain

```sql
-- Oracle
TYPE number_array IS TABLE OF NUMBER;
TYPE id_array IS VARRAY(20) OF NUMBER;

-- PostgreSQL
CREATE DOMAIN number_array AS numeric[];
CREATE DOMAIN id_array     AS numeric[];
```

A **domain** (rather than using `numeric[]` inline) keeps the original type name visible in
signatures, so calling code and parameter lists need no churn. Note the `VARRAY` size bound
is *not* enforced by the domain — add `CHECK (cardinality(VALUE) <= 20)` if the limit is
semantically required.

---

## 4. The accumulate-then-return rewrite → `RETURN NEXT`

The dominant Oracle pattern: build up a collection in a loop, return it at the end.

```sql
-- Oracle
t_avail  rtsng_t_avail := rtsng_t_avail();
i        NUMBER := 1;
BEGIN
  FOR rec IN (SELECT ...) LOOP
    t_avail.EXTEND(1);
    t_avail(i) := rtsng_type_avail(NULL, NULL, ...);   -- new element
    t_avail(i).id       := rec.id;                     -- populate fields
    t_avail(i).noka     := rec.noka;
    i := i + 1;
  END LOOP;
  RETURN t_avail;
END;
```

```sql
-- PostgreSQL
DECLARE rec_avail rtsng_type_avail;
BEGIN
  FOR rec IN (SELECT ...) LOOP
    rec_avail := NULL::rtsng_type_avail;   -- start a new row
    rec_avail.id   := rec.id;
    rec_avail.noka := rec.noka;
    RETURN NEXT rec_avail;                 -- emit the row
  END LOOP;
  RETURN;
END;
```

Mapping rules:

| Oracle | PostgreSQL |
|---|---|
| accumulator variable declaration | a single **row variable** (`rec_<name>`) |
| `coll.EXTEND` + constructor call | `rec := NULL::<type>` (reset all fields) |
| `coll(i).field := x` | `rec.field := x` |
| end of one element's assignments | `RETURN NEXT rec;` |
| `RETURN coll;` | `RETURN;` |
| the `i := i + 1` index counter | delete — no longer needed |

> ### The row boundary is the hazard
> Deciding *where one element ends* is the only judgement call, and it is easy to get
> wrong. Automating it as "the end of a consecutive run of field assignments" handles the
> common case but **split one Oracle element into three rows** in a function with branching
> assignments — silently changing result cardinality, with no error at `CREATE` time and no
> syntax check that can catch it.
>
> Treat every automated row boundary as requiring human review. There must be exactly one
> `RETURN NEXT` per Oracle `coll(i)` element, including across `IF`/`CASE` branches.

---

## 5. Collection methods → array operations

| Oracle | PostgreSQL |
|---|---|
| `coll(i)` | `coll[i]` (both are 1-based) |
| `coll.COUNT` | `cardinality(coll)` |
| `coll.FIRST` / `coll.LAST` | `1` / `cardinality(coll)` |
| `coll.EXTEND` / `coll.EXTEND(n)` | not needed — drop |
| `coll.TRIM` | not needed — drop |
| `coll.DELETE` | `coll := '{}'` |
| `coll.EXISTS(i)` | `coll[i] IS NOT NULL` |
| `coll.EXTEND; coll(coll.LAST) := v` | `coll := array_append(coll, v)` |
| `x MEMBER OF coll` | `x = ANY(coll)` |
| `x NOT MEMBER OF coll` | `NOT (x = ANY(coll))` |
| `TABLE(coll)` in a `FROM` clause | `unnest(coll)` |

**NULL guard.** `FOR i IN 1..coll.COUNT` is safe in Oracle when the collection is empty,
but `cardinality(NULL)` is **NULL** in PostgreSQL and the loop misbehaves. Always write:

```sql
FOR i IN 1..COALESCE(cardinality(coll), 0) LOOP
```

---

## 6. Associative arrays (`INDEX BY`) have no equivalent

`TYPE t IS TABLE OF x INDEX BY PLS_INTEGER` (or `INDEX BY VARCHAR2(...)`) is a **sparse
map**. PostgreSQL arrays are dense and integer-indexed.

- Integer-keyed and used sequentially → an array is fine.
- Genuinely sparse, or string-keyed → restructure: a `jsonb` value, a temporary relation,
  or (usually best) the query the map was caching.

Do not pretend an array is equivalent to a sparse map — lookups by a missing key behave
differently and silently.

---

## 7. `SYS_REFCURSOR` → `refcursor`

Map in return types, parameters and declarations; `OPEN c FOR <query>` works in PL/pgSQL.

However, `refcursor` OUT parameters are a poor fit for most modern clients (the cursor must
be fetched in the same transaction). Prefer `RETURNS SETOF` / `RETURNS TABLE` unless the
caller genuinely streams the cursor.

---

## 8. `BULK COLLECT` and `FORALL` → one set-based statement

PostgreSQL has no `FORALL`. Rather than emulating it, collapse the pair into the set-based
DML that the Oracle code was hand-rolling in the first place:

```sql
-- Oracle
SELECT * BULK COLLECT INTO recs FROM t WHERE ...;
FORALL i IN 1..recs.COUNT
  UPDATE tbl SET c = recs(i).c WHERE k = recs(i).k;

-- PostgreSQL — preferred: one statement, no collection at all
UPDATE tbl SET c = s.c FROM unnest(recs) s WHERE tbl.k = s.k;
-- or, better still, skip the intermediate entirely:
UPDATE tbl SET c = t.c FROM t WHERE tbl.k = t.k AND ...;
```

When the collection is genuinely needed (returned to a caller, or reused):

```sql
SELECT array_agg(t) INTO recs FROM t WHERE ...;   -- array of the table's row type
```

`array_agg` does **not** guarantee ordering; add `ORDER BY` if the Oracle loop's order
mattered (`array_agg(t ORDER BY t.k)`).

---

## 9. PostgreSQL cannot make arrays of anonymous records — a real blocker

Oracle code frequently prefetches into a collection of an *anonymous* record type
(a `TABLE OF` a `%ROWTYPE` or an ad-hoc record), then loops with an index match.
PostgreSQL has **no array-of-anonymous-record type**, so there is nothing to declare.

Resolution: **delete the prefetch and use the query directly.**

```sql
-- Oracle (paraphrased): cache rows, then index-match in a loop
TYPE rec_tab IS TABLE OF some_query%ROWTYPE;
cache rec_tab;
SELECT ... BULK COLLECT INTO cache FROM ...;
FOR i IN 1..cache.COUNT LOOP
  IF cache(i).key = needle THEN ... END IF;
END LOOP;

-- PostgreSQL: query what you need, let the planner do the caching
FOR rec IN SELECT ... FROM ... WHERE key = needle LOOP
  ...
END LOOP;
```

This is logic-equivalent and usually *faster*: the "optimisation" was hand-rolled caching
that the PostgreSQL planner and buffer cache already do. Two ~900-line functions were
resolved this way.

If a named composite type would work (all fields known and stable), declaring
`CREATE TYPE ... AS (...)` and using `<type>[]` is the alternative — but prefer removing
the cache.

---

## 10. Package-level types are not migrated

References like `pkg_types.some_type` are Oracle **package** types. AWS SCT/DMS SC does not
migrate packages, so these declarations have no target object. Options:

1. Restructure to iterate the query directly (**preferred** — a package collection type is
   almost always a cache of a query).
2. An array of the table's row type: `schema.tbl[]`.
3. An explicit schema-level composite type.

Surface these during Inception: they look like ordinary type references but have no
migration path, so they are effort that assessment tools under-count.

---

## 11. Review checklist

- [ ] Every Oracle collection type resolved to `SETOF` / domain / restructure — none left as a bare type reference
- [ ] Collection types mapped consistently across return types, **parameters** and local declarations
- [ ] Exactly one `RETURN NEXT` per source element, verified by a human (§4)
- [ ] Every `1..coll.COUNT` loop wrapped in `COALESCE(cardinality(...), 0)`
- [ ] `BULK COLLECT` + `FORALL` pairs collapsed to set-based DML, not emulated
- [ ] `array_agg` given an explicit `ORDER BY` where order was significant
- [ ] No attempt to build an array of an anonymous record (§9)
- [ ] Associative arrays restructured, not silently turned into dense arrays (§6)
- [ ] Result **cardinality** compared against the source for every rewritten set-returning
      function — the row-boundary hazard changes row counts without any error
