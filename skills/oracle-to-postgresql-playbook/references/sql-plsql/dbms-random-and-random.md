# DBMS_RANDOM and PostgreSQL RANDOM

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.random.html

**Conversion category:** Manual (Three-star feature compatibility, no automation; different syntax requires code rewrite; no 1:1 package)
**SCT automation:** No automation; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 16/17 `random(min,max)`, `random_normal()` (verified), orafce `dbms_random` (verified), inclusive/exclusive range caveat.

## Oracle

`DBMS_RANDOM` generates random numbers/strings. Procedures:
- **NORMAL** — random numbers in standard normal distribution.
- **SEED** — reset the seed.
- **STRING** — random string (first char = type, number = length).
- **VALUE** — number in [0,1) with 38 decimal digits, or in [low, high).

`DBMS_RANDOM.RANDOM` returns integers in [-2^31, 2^31]. `DBMS_RANDOM.VALUE` returns [0,1] with 38-digit precision.

```sql
select dbms_random.value() from dual;        -- e.g. .859251508
select dbms_random.string('p',10) from dual; -- e.g. la'?z[Q&/2
```

## PostgreSQL

Core PostgreSQL has no package, but built-ins now cover most uses (verified on 18.6):
- Random number in [0,1): `random()`
- Random integer in [min, max] **inclusive**: `random(1, 100)` (PG 17+); random numeric: `random(1.0, 100.0)` (PG 17+)
- Normally distributed: `random_normal(mean => 0, stddev => 1)` (PG 16+) ≈ `DBMS_RANDOM.NORMAL`
- Seed: `setseed(0.5)` ≈ `DBMS_RANDOM.SEED`
- Random string (hex): `md5(random()::text)`; random UUID: `gen_random_uuid()` / `uuidv7()` (PG 18)
- **orafce** `dbms_random` package (Aurora 18): `dbms_random.value(low, high)`, `dbms_random.string('U', 10)`, `dbms_random.normal()`, `dbms_random.seed(...)`, all verified. It is the lowest-effort conversion when the code uses `STRING` with option letters.

```sql
select random();              -- e.g. 0.866594325285405
select md5(random()::text);   -- e.g. f83e73114eccfed571b43777b99e0795
```

Random string of a specified length via a helper function:

```sql
create or replace function random_string(length integer) returns text as
$$
declare
  chars text[] := '{0,1,2,3,4,5,6,7,8,9,A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z}';
  result text := '';
  i integer := 0;
begin
  if length < 0 then
    raise exception 'Given length cannot be less than 0';
  end if;
  for i in 1..length loop
    result := result || chars[1+random()*(array_length(chars, 1)-1)];
  end loop;
  return result;
end;
$$ language plpgsql;

select random_string(15);  -- e.g. 5emZKMYxB9C2vT6
```

## Summary

| Description | Oracle | PostgreSQL |
|---|---|---|
| Random number | `select dbms_random.value() from dual;` | `select random();` |
| Random number 1..100 | `select dbms_random.value(1,100) from dual;` | `select random(1.0, 100.0);` (PG 17+); integer: `select random(1, 100);` |
| Normal distribution | `select dbms_random.normal from dual;` | `select random_normal();` (PG 16+) |
| Random string | `select dbms_random.string('p',10) from dual;` | `select md5(random()::text);` |
| Random string upper case | `select dbms_random.string('U',10) from dual;` | `select upper(md5(random()::text));` |

## Conversion notes

- `dbms_random.value()` → `random()`; ranged `dbms_random.value(low,high)` → `random(low::numeric, high::numeric)` on PG 17+ (or `low + random()*(high-low)`). Note `random(int, int)` includes `high`, while Oracle `VALUE(low, high)` excludes it.
- `dbms_random.string(...)` → `md5(random()::text)` for hex strings, or a custom `random_string()` function for arbitrary character sets/lengths.
- `DBMS_RANDOM.NORMAL` → `random_normal()` (PG 16+); `DBMS_RANDOM.SEED` → `setseed()`.
- None of these are cryptographically secure. For tokens, use `gen_random_uuid()` or `pgcrypto`'s `gen_random_bytes()`.
- Note `md5(random()::text)` only yields hex chars (0-9a-f); use the helper function when you need full alphanumeric output.
