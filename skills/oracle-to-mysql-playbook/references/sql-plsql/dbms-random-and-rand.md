# DBMS_RANDOM and RAND

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.random.html

**Conversion category:** Manual (★★★ feature compatibility, no automation)
**SCT automation:** N/A — different syntax and missing options may require code rewrite.

## Oracle

`DBMS_RANDOM` generates random numbers/strings in SQL or PL/SQL. Subprograms:
* **NORMAL** — random numbers in a standard normal distribution.
* **SEED** — resets the seed.
* **STRING** — random string.
* **VALUE** — number `>= 0` and `< 1` with 38 decimal digits; or a number between low/high params.

`DBMS_RANDOM.RANDOM` → integers in [-2^31, 2^31]. `DBMS_RANDOM.VALUE` → [0,1] with 38 digits precision.

```sql
-- Random number
select dbms_random.value() from dual;   -- .859251508

-- Random string ('p' = printable, length 10)
select dbms_random.string('p',10) from dual;   -- la'?z[Q&/2
```

## MySQL

`RAND()` returns a float `v` where `0 <= v < 1.0`. It does **not** generate strings — combine with other functions. With an integer seed `N`: a constant initializer seeds once at prepare time; a non-constant initializer (e.g., column) re-seeds on each invocation.

```sql
-- Random number
SELECT RAND();   -- 0.30244802525494996

-- Random integer in range i <= R < j:  FLOOR(i + RAND() * (j - i))
SELECT FLOOR(7 + (RAND() * 5));   -- range 7..11

-- 8-char string of hex digits
SELECT SUBSTRING(MD5(RAND()) FROM 1 FOR 8);

-- 8-char alphabetic string
SELECT concat(
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1),
  substring('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', rand()*52+1, 1));
```

## Conversion notes

| Oracle | MySQL |
|---|---|
| `DBMS_RANDOM.VALUE()` (0..1) | `RAND()` |
| `DBMS_RANDOM.VALUE(low,high)` | `low + RAND() * (high - low)` |
| `DBMS_RANDOM.RANDOM` (integer) | `FLOOR(i + RAND() * (j - i))` |
| `DBMS_RANDOM.STRING(...)` | `SUBSTRING(MD5(RAND()) ...)` or `CONCAT(SUBSTRING('A..z', RAND()*52+1, 1), ...)` |
| `DBMS_RANDOM.SEED(n)` | `RAND(n)` (integer seed) |
| `DBMS_RANDOM.NORMAL` | no direct equivalent — implement (e.g., Box-Muller) |

- `RAND()` only produces numbers — random strings must be built from `MD5`/`SUBSTRING`/`CONCAT` expressions.
- No standard-normal-distribution function in MySQL; implement manually if `NORMAL` is needed.
