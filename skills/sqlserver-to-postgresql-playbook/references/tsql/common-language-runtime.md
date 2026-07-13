# Common Language Runtime (CLR)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.clr.html

**Conversion category:** Manual (one-star feature compatibility — full code rewrite required)
**SCT automation:** No automation; N/A action code

## SQL Server

SQL Server can implement .NET objects in the database using the Common Language Runtime (CLR), enabling functionality that would be complicated in T-SQL — robust string manipulation, date manipulation, and calling external services (WCF services, web services).

Objects created with the `EXTERNAL NAME` clause:
- Procedures (CLR Stored Procedures)
- Functions (CLR Functions)
- Triggers (CLR Triggers)
- Types (CLR User-Defined Types)
- User-defined aggregate functions (CLR User-Defined Aggregates)

## PostgreSQL

Aurora PostgreSQL does **not** support .NET code. Convert all C# CLR code to **PL/pgSQL** or **PL/Perl**.

To use PL/Perl, install the extension:

```sql
CREATE EXTENSION plperl;
```

Then create functions with `LANGUAGE plperl`. You can create: functions, void functions/procedures, triggers, event triggers, and session-level values.

Example — return the greater of two integers:

```sql
CREATE FUNCTION perl_max (integer, integer) RETURNS integer AS $$
  if ($_[0] > $_[1]) { return $_[0]; }
  return $_[1];
$$ LANGUAGE plperl;
```

## Conversion notes
- Migrating CLR objects requires a **full code rewrite** — no automation.
- Rewrite .NET/C# logic in PL/pgSQL (preferred for DB logic) or PL/Perl (for complex string/date manipulation).
- External service calls (WCF/web services) from CLR have no in-database equivalent; re-architect using AWS Lambda or application-tier code.
- PL/Perl requires the `plperl` extension to be installed.
