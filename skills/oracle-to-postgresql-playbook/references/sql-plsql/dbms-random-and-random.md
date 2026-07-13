# DBMS_RANDOM and PostgreSQL RANDOM

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.random.html

**Conversion category:** Manual (Three-star feature compatibility, no automation; different syntax requires code rewrite; no 1:1 package)
**SCT automation:** No automation; SCT action code index N/A

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

No dedicated package; no 1:1 migration. Use built-ins as workarounds:
- Random number: `random()`
- Random string: `md5(random()::text)`

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
| Random number 1..100 | `select dbms_random.value(1,100) from dual;` | `select random()*100;` |
| Random string | `select dbms_random.string('p',10) from dual;` | `select md5(random()::text);` |
| Random string upper case | `select dbms_random.string('U',10) from dual;` | `select upper(md5(random()::text));` |

## Conversion notes

- `dbms_random.value()` → `random()`; ranged `dbms_random.value(low,high)` → `low + random()*(high-low)` (playbook shows `random()*100` for 1..100).
- `dbms_random.string(...)` → `md5(random()::text)` for hex strings, or a custom `random_string()` function for arbitrary character sets/lengths.
- `DBMS_RANDOM.NORMAL`/`SEED` have no direct equivalents; use `setseed()` for reproducible sequences and custom math for normal distribution.
- Note `md5(random()::text)` only yields hex chars (0-9a-f); use the helper function when you need full alphanumeric output.
