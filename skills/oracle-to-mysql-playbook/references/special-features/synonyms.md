# Oracle Synonyms

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.synonyms.html

**Conversion category:** Manual (one-star feature compatibility; one-star automation) — use stored procedures/functions/views to abstract objects.
**SCT automation:** No automation. SCT action code index: Synonyms.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Still no synonyms on 3 / 8.4; view-based synonyms are updatable (verified), SELECT * freeze, public-synonym strategy.

## Oracle

A synonym is an alternative name for a schema object (table, view, sequence, procedure, function, package, materialized view, Java object, or another synonym). The referenced object is the "base object" and can be in the same database, another database on the same instance, or a remote server. Synonyms provide an abstraction layer isolating application code from changes to a base object's name or location (e.g., moving a table to another schema requires only updating the synonym, not the application).

Syntax:

```sql
CREATE [OR REPLACE] [EDITIONABLE | NONEDITIONABLE]
[PUBLIC] SYNONYM [schema .] synonym_name
FOR [schema .] object_name [@ dblink];
```

Example:

```sql
CREATE SYNONYM local_emps FOR usa.emps;
```

## MySQL

Aurora MySQL does **not** support synonyms and there is no generic workaround. Partial approaches:

- Use **encapsulating views** as an abstraction layer over tables/views.
- Use **functions or stored procedures** that call other functions/procedures.

Synonyms are often used together with database links, which Aurora MySQL also does not support.

```sql
-- view as a partial synonym substitute
CREATE VIEW local_emps AS SELECT * FROM usa.emps;
```

## Conversion notes

- No direct equivalent; replace synonyms with views (for tables/views) or wrapper stored procedures/functions (for callable objects).
- Fully-qualified `database.table` names can reference objects in another database within the same cluster.
- Synonyms pointing at remote objects via database links cannot be reproduced (no DB links in MySQL) — re-architect.
- Still no `CREATE SYNONYM` on Aurora MySQL 3 / 8.4. A single-table view `CREATE VIEW local_emps AS SELECT * FROM usa.emps` is updatable, so `INSERT`/`UPDATE`/`DELETE` through it work (verified on both versions). `SELECT *` is expanded at creation, so recreate the view after adding columns to the base table.
- Public synonyms (used so code can omit the owner) → convert to fully-qualified `db.object` names during conversion (SCT does the same, action code 352), or connect with the application's default database set to the owning schema.
- Synonyms for sequences, packages or types have no equivalent; resolve them to the converted object names.
