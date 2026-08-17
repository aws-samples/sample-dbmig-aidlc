# Partitioning — rules that fail at RUNTIME or change semantics (Oracle → PostgreSQL)

This file is **injected into every conversion prompt**, so it is deliberately short. It carries
only the partitioning rules whose violation does **not** announce itself at `CREATE` time:
either the DDL succeeds and the application breaks later, or the DDL succeeds and quietly means
something different.

Compile-time partitioning errors (wrong syntax, missing bound) are self-revealing — the apply
step reports them and the retry loop feeds the error back. Those, plus the full treatment of
list/range/hash/composite partitioning, live in
[`skills/oracle-to-postgresql-playbook/references/physical-storage/table-partitioning-and-inheritance.md`](../../../skills/oracle-to-postgresql-playbook/references/physical-storage/table-partitioning-and-inheritance.md)
— **open it whenever a table is partitioned.**

---

## 1. Every partitioned table needs a `DEFAULT` partition — RUNTIME failure

Oracle routes NULL and out-of-range partition keys to a catch-all. PostgreSQL **rejects the
insert**: `SQLSTATE 23514 — no partition of relation "t" found for row`.

```sql
CREATE TABLE t_default PARTITION OF t DEFAULT;
```

Emit one for **every** partitioned table, range and list alike. Omitting it converts cleanly,
passes a schema diff, survives a data load of existing rows, and then fails in production on the
first out-of-range insert. Nothing earlier in the pipeline catches it.

## 2. Range partitions need two-sided bounds starting at `MINVALUE`

Oracle gives only an upper bound (`VALUES LESS THAN`). PostgreSQL needs `FOR VALUES FROM (...)
TO (...)`, where `FROM` is inclusive and `TO` is exclusive. Carry each partition's upper bound
forward as the next one's lower bound and start the first at `MINVALUE`:

```sql
CREATE TABLE p18 PARTITION OF t FOR VALUES FROM (MINVALUE)              TO ('2019-01-01');
CREATE TABLE p19 PARTITION OF t FOR VALUES FROM ('2019-01-01')          TO ('2020-01-01');
```

Starting the first partition at the earliest *data* value instead of `MINVALUE` leaves older
rows with no home — again a runtime insert failure, not a conversion error.

## 3. PK/UNIQUE must include the partition key — SEMANTIC CHANGE

PostgreSQL: `unique constraint on partitioned table must include all partitioning columns`.
Oracle allows a global unique index that excludes the partition key; PostgreSQL does not.

Adding the partition key makes the DDL work but **weakens uniqueness from global to
per-partition-key-value** — rows Oracle would have rejected can now coexist. This compiles, so
no test that only checks "does it load" will catch it.

Required: apply the change, mark it inline (`-- NOTE: uniqueness weakened to per-partition ...`),
and record it as a semantic change needing sign-off. Never do it silently.

Also: `DEFERRABLE` unique constraints are unsupported on partitioned tables — Oracle's
deferred-to-`COMMIT` checking becomes per-statement checking.

## 4. Partition names are schema-global — silent collision risk

Oracle scopes partition names per table; PostgreSQL partitions are ordinary relations, so
`SALES.P_2019` and `ORDERS.P_2019` collide (`relation "p_2019" already exists`). Track emitted
partition names **globally**, prefix with the parent table on collision, and truncate to the
**63-byte** identifier limit — then re-check that truncation did not create a fresh collision.

## 5. Triggers/indexes/FKs on a partitioned parent clone to every partition

Declaring a `FOR EACH ROW` trigger on the parent creates one per partition (175 declarations →
668 `pg_trigger` rows in one real migration). Correct behaviour, but reconciliation must compare
**parent declarations**, not raw catalog counts, or it reports a false mismatch.

---

## Unsupported Oracle partitioning features — flag, don't approximate

`INTERVAL`, `REFERENCE`, virtual-column-based, automatic-list, and `SPLIT`/`EXCHANGE PARTITION`
have no declarative equivalent. Composite/sub-partitioning is expressible by nesting
`PARTITION BY` inside `PARTITION OF`. Interval and automatic-list partitioning rely on Oracle
creating partitions on demand — in PostgreSQL either pre-create them, manage them with
`pg_partman`, or rely on the `DEFAULT` partition (rule 1) to absorb the overflow. Surface the
choice; do not silently drop the behaviour.
