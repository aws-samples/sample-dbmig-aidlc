# Common Language Runtime (CLR)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.clr.html

**Conversion category:** Manual (one-star feature compatibility — full code rewrite required)
**SCT automation:** No automation; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PL/v8 and `pg_tle`, unavailable languages (verified), `aws_lambda` for external calls (C# Lambdas), CLR use cases now native, aggregates/types mapping.

## SQL Server

SQL Server can implement .NET objects in the database using the Common Language Runtime (CLR), enabling functionality that would be complicated in T-SQL — robust string manipulation, date manipulation, and calling external services (WCF services, web services).

Objects created with the `EXTERNAL NAME` clause:
- Procedures (CLR Stored Procedures)
- Functions (CLR Functions)
- Triggers (CLR Triggers)
- Types (CLR User-Defined Types)
- User-defined aggregate functions (CLR User-Defined Aggregates)

## PostgreSQL

Aurora PostgreSQL does **not** support .NET code. Convert C# CLR code to **PL/pgSQL**, **PL/Perl**, or **PL/v8** (JavaScript, 3.2.4 on Aurora 18). `pg_tle` (Trusted Language Extensions) can package such code as a versioned extension. PL/Python, PL/Java and custom C extensions are **not** available on Aurora 18 (checked 18.6).

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
- External service calls (WCF/web services) from CLR → **`aws_lambda.invoke(...)`** from SQL (aws_lambda 2.1 on Aurora 18; synchronous `'RequestResponse'` or async `'Event'`), or application-tier code. The Lambda function can be written in C#/.NET, so existing CLR logic can often be reused there.
- Common CLR use cases now native in PostgreSQL: regular expressions (`regexp_like/replace/substr/count`), string splitting (`string_to_table`), JSON (`jsonb`, SQL/JSON `json_table` PG 17), and date arithmetic (intervals).
- CLR user-defined aggregates → `CREATE AGGREGATE` with a PL/pgSQL state function. CLR user-defined types → composite types or domains.
- PL/Perl requires the `plperl` extension to be installed.
