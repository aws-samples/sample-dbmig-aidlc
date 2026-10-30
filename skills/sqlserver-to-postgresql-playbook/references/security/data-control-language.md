# Data Control Language (GRANT / REVOKE)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.security.datacontrollanguage.html

**Conversion category:** Automatic (five-star compatibility — similar syntax and similar functionality)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `GRANT … ON PROCEDURE` (verified), EXECUTE default to PUBLIC, fixed-role mapping incl. cluster-wide predefined roles, PG 15 public-schema change, RLS mapping.

## SQL Server

The ANSI standard uses `GRANT` and `REVOKE` to control permissions. SQL Server additionally provides a `DENY` command to explicitly restrict access. `DENY` takes precedence over `GRANT` and resolves conflicting permissions for users with multiple logins (e.g., a user DENY'd via group membership but GRANT'd via personal login is denied).

Permissions can be granted at multiple levels, from low-level objects (columns) to high-level objects (servers), and are categorized for specific services/features (e.g., service broker). Permissions work together with database users and roles.

Syntax (simplified):

```sql
GRANT { ALL [ PRIVILEGES ] } | <permission> [ ON <securable> ] TO <principal>

DENY { ALL [ PRIVILEGES ] } | <permission> [ ON <securable> ] TO <principal>

REVOKE [ GRANT OPTION FOR ] {[ ALL [ PRIVILEGES ] ]|<permission>} [ ON <securable> ] { TO | FROM } <principal>
```

## PostgreSQL

Aurora PostgreSQL supports the ANSI DCL commands `GRANT` and `REVOKE`. Permissions can be granted on individual objects (column, function, table) or on multiple objects via `ALL <TABLES|SEQUENCES|FUNCTIONS> IN SCHEMA`.

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA <Schema Name> TO <Role Name>;
```

`WITH GRANT OPTION` (equivalent to SQL Server's `WITH GRANT OPTION`) lets the grantee further grant the same permission to others:

```sql
GRANT EXECUTE
ON FUNCTION demo.Procedure1
TO UserY
WITH GRANT OPTION;
```

Available privileges:

| Permission | Use to |
|---|---|
| `SELECT` | Query rows from a table |
| `INSERT` | Insert rows into a table |
| `UPDATE` | Update rows in a table |
| `DELETE` | Delete rows from a table |
| `TRUNCATE` | Truncate a table |
| `REFERENCES` | Create a foreign key constraint |
| `TRIGGER` | Create a trigger on the table |
| `CREATE` | Purpose depends on target object |
| `CONNECT` | Connect to the specified database |
| `TEMPORARY` / `TEMP` | Create temporary tables |
| `EXECUTE` | Run a function |
| `USAGE` | Purpose depends on target object |
| `ALL` / `ALL PRIVILEGES` | Grant all available privileges |

Syntax (selected forms):

```sql
GRANT { { SELECT | INSERT | UPDATE | DELETE | TRUNCATE | REFERENCES | TRIGGER }
  [, ...] | ALL [ PRIVILEGES ] }
  ON { [ TABLE ] table_name [, ...]
    | ALL TABLES IN SCHEMA schema_name [, ...] }
  TO role_specification [, ...] [ WITH GRANT OPTION ]

GRANT { { SELECT | INSERT | UPDATE | REFERENCES } ( column_name [, ...] )
  [, ...] | ALL [ PRIVILEGES ] ( column_name [, ...] ) }
  ON [ TABLE ] table_name [, ...]
  TO role_specification [, ...] [ WITH GRANT OPTION ]

GRANT { { USAGE | SELECT | UPDATE }
  [, ...] | ALL [ PRIVILEGES ] }
  ON { SEQUENCE sequence_name [, ...]
    | ALL SEQUENCES IN SCHEMA schema_name [, ...] }
  TO role_specification [, ...] [ WITH GRANT OPTION ]

GRANT { { CREATE | CONNECT | TEMPORARY | TEMP } [, ...] | ALL [ PRIVILEGES ] }
  ON DATABASE database_name [, ...]
  TO role_specification [, ...] [ WITH GRANT OPTION ]

GRANT { EXECUTE | ALL [ PRIVILEGES ] }
  ON { FUNCTION function_name ( [ [ argmode ] [ arg_name ] arg_type [, ...] ] ) [,...]
    | ALL FUNCTIONS IN SCHEMA schema_name [, ...] }
  TO role_specification [, ...] [ WITH GRANT OPTION ]

GRANT { { CREATE | USAGE } [, ...] | ALL [ PRIVILEGES ] }
  ON SCHEMA schema_name [, ...]
  TO role_specification [, ...] [ WITH GRANT OPTION ]

-- role_specification can be:
--   [ GROUP ] role_name | PUBLIC | CURRENT_USER | SESSION_USER

GRANT role_name [, ...] TO role_name [, ...] [ WITH ADMIN OPTION ]
```

(Additional `GRANT` forms exist for DOMAIN, FOREIGN DATA WRAPPER, FOREIGN SERVER, LANGUAGE, LARGE OBJECT, TABLESPACE, and TYPE.)

Examples:

```sql
-- Grant SELECT on all tables in a schema
GRANT SELECT ON ALL TABLES IN SCHEMA emps TO John;

-- Revoke EXECUTE on a stored procedure (function)
REVOKE EXECUTE ON FUNCTION EmployeeReport FROM John;
```

## Conversion notes

- `GRANT` and `REVOKE` are largely portable — syntax and functionality are very similar between the engines.
- **No `DENY` in PostgreSQL.** SQL Server's `DENY` (which takes precedence over GRANT) has no direct equivalent. Re-model deny logic by not granting the permission, or by carefully structuring role membership. Review any DENY usage during migration since revoking is not the same as explicit deny.
- SQL Server stored procedures map to PostgreSQL **procedures** or functions: `GRANT EXECUTE ON PROCEDURE p(int) TO r` (verified) or `ON FUNCTION`. Include argument types when the name is overloaded. `ALL PROCEDURES IN SCHEMA` / `ALL ROUTINES IN SCHEMA` cover both.
- `EXECUTE` is granted to `PUBLIC` by default on new functions and procedures (SQL Server grants nothing by default). Run `REVOKE EXECUTE ON … FROM PUBLIC` for sensitive routines, or `ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON ROUTINES FROM PUBLIC`.
- SQL Server fixed database roles → PostgreSQL:

  | SQL Server | Aurora PostgreSQL 18 |
  |---|---|
  | `db_owner` | owner of the database (`pg_database_owner` refers to it) plus ownership of the schemas |
  | `db_datareader` | `GRANT SELECT ON ALL TABLES IN SCHEMA s` + default privileges per schema. `pg_read_all_data` (PG 14) is **cluster-wide** (every database), so use it only when that scope is intended |
  | `db_datawriter` | `GRANT INSERT, UPDATE, DELETE …` per schema; `pg_write_all_data` (PG 14) is cluster-wide |
  | `db_ddladmin` | `GRANT CREATE ON SCHEMA s` |
  | `db_securityadmin` | `CREATEROLE` (PG 16 semantics: only manages roles it created or holds `ADMIN` on) |
  | `db_backupoperator` | N/A (backups are managed by Aurora) |
  | `VIEW SERVER STATE` | `pg_monitor`, `pg_read_all_stats` |
  | `ALTER ANY` maintenance | `pg_maintain` (PG 17) or `GRANT MAINTAIN ON t` |
- Since PostgreSQL 15, `PUBLIC` cannot create objects in the `public` schema (verified on 18.6), which matches SQL Server's default where users cannot create in `dbo`.
- **Row-Level Security** (SQL Server security policies + predicate functions) → PostgreSQL RLS: `ALTER TABLE t ENABLE ROW LEVEL SECURITY; CREATE POLICY … USING (…) WITH CHECK (…);` (verified).
- Use `ALL TABLES|SEQUENCES|FUNCTIONS IN SCHEMA` for bulk grants. Note these apply only to existing objects; use `ALTER DEFAULT PRIVILEGES` for future objects.
- `WITH GRANT OPTION` maps directly; role-to-role grants use `WITH ADMIN OPTION`.
