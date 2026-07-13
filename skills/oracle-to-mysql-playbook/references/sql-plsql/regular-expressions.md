# Regular Expressions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.regularexpressions.html

**Conversion category:** Assisted (★★★ feature compatibility, ★★★ automation)
**SCT automation:** N/A — syntax and option differences.

## Oracle

Oracle SQL regex follows POSIX 1003.2/D11.2 and Unicode guidelines, extended with multilingual matching and some PERL operators (character class shortcuts, non-greedy `?`). Functions:
* `REGEXP_LIKE` — match rows in `WHERE`.
* `REGEXP_COUNT` — number of pattern occurrences.
* `REGEXP_INSTR` — position of a pattern.
* `REGEXP_REPLACE` — replace pattern, return new string.
* `REGEXP_SUBSTR` — return the matching substring.

Match options: `i` (case-insensitive), `c` (case-sensitive), `n` (`.` matches newline), `m` (multiline), `x` (ignore whitespace in pattern).

```sql
-- Steven or Stephen
SELECT * FROM EMPLOYEES WHERE REGEXP_LIKE(first_name, '^Ste(v|ph)en$');

-- 'g' (case-sensitive) twice from position 3
SELECT * FROM EMPLOYEES WHERE REGEXP_COUNT('George Washington', 'g', 3, 'c') = 2;

-- valid email
SELECT * FROM EMPLOYEES WHERE REGEXP_INSTR(email, '\w+@\w+(\.\w+)+') > 0;

-- space after each character
SELECT REGEXP_REPLACE(country_name, '(.)', '\1 ') FROM EMPLOYEES;
```

## MySQL

Aurora MySQL uses Henry Spencer's POSIX 1003.2 regex (extended). Operators:
* `REGEXP` / `RLIKE` — returns 1 if match, 0 if not, NULL if either arg NULL.
* `NOT REGEXP` / `NOT RLIKE` — inverse.

`RLIKE` is a synonym for `REGEXP`. MySQL uses C escape syntax — **double any `\`** in REGEXP arguments.

> Note: Amazon RDS for MySQL 8.0 adds Oracle-like regex functions (`REGEXP_LIKE`, `REGEXP_REPLACE`, `REGEXP_INSTR`, `REGEXP_SUBSTR`).

```sql
-- Steven or Stephen
SELECT * FROM EMPLOYEES WHERE first_name REGEXP ('^Ste(v|ph)en$');

-- valid email
SELECT * FROM EMPLOYEES WHERE email NOT REGEXP '^[A-Z0-9._%-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}$';
```

## Conversion notes

| Usage | Oracle | MySQL (5.7) |
|---|---|---|
| Match (Steven/Stephen) | `REGEXP_LIKE(first_name, '^Ste(v\|ph)en$')` | `first_name REGEXP ('^Ste(v\|ph)en$')` |
| Count occurrences | `REGEXP_COUNT('George Washington','g',3,'c')=2` | `LENGTH(SUBSTRING(FULL_NAME,3)) - LENGTH(REPLACE(SUBSTRING(FULL_NAME,3),'g','')) = 2` |
| Position / validate | `REGEXP_INSTR(email,'\w+@\w+(\.\w+)+')>0` | `email NOT REGEXP '^[A-Z0-9._%-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}$'` |
| Replace pattern | `REGEXP_REPLACE(country_name,'(.)','\1 ')` | Use a user-defined function (no `REGEXP_REPLACE` in 5.7) |

- Aurora MySQL 5.7 only has the `REGEXP`/`RLIKE` match operators — no `REGEXP_COUNT`/`INSTR`/`REPLACE`/`SUBSTR`. Simulate counting via `LENGTH`/`REPLACE`, and replacement via a UDF.
- Escape backslashes (`\\`) in MySQL patterns.
- Match flags (`i`/`c`/`n`/`m`/`x`) are expressed differently — MySQL relies on collation case-sensitivity and inline modifiers.
- If targeting MySQL 8, the Oracle-style `REGEXP_*` functions are available — near-direct migration.
