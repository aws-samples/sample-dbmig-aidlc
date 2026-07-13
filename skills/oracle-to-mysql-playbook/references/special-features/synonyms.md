# Oracle Synonyms

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.synonyms.html

**Conversion category:** Manual (one-star feature compatibility; one-star automation) — use stored procedures/functions/views to abstract objects.
**SCT automation:** No automation. SCT action code index: Synonyms.

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
