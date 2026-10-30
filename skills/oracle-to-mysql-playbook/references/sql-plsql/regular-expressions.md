# Regular Expressions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.regularexpressions.html

**Conversion category:** Assisted (★★★ feature compatibility, ★★★ automation)
**SCT automation:** N/A — syntax and option differences.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): REGEXP_LIKE/INSTR/SUBSTR/REPLACE are native on 3 / 8.4; no REGEXP_COUNT (verified); case follows collation (add 'c'), 'x' flag rejected, $1 back-references, escaping, occurrence args — all verified; 5.7 notes marked legacy.

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

**Aurora MySQL 3 and 8.4 provide `REGEXP_LIKE`, `REGEXP_INSTR`, `REGEXP_SUBSTR` and `REGEXP_REPLACE`** (ICU regex library), plus the `REGEXP`/`RLIKE` operators (verified on 3.13.0 and 8.4.8). There is **no `REGEXP_COUNT`** (error 1305, verified).

```sql
-- Steven or Stephen
SELECT * FROM employees WHERE REGEXP_LIKE(first_name, '^Ste(v|ph)en$', 'c');

-- 'g' (case-sensitive) twice from position 3  (no REGEXP_COUNT)
SELECT * FROM employees
WHERE CHAR_LENGTH(SUBSTRING(full_name, 3))
    - CHAR_LENGTH(REGEXP_REPLACE(SUBSTRING(full_name, 3), 'g', '', 1, 0, 'c')) = 2;

-- valid email
SELECT * FROM employees WHERE REGEXP_INSTR(email, '\\w+@\\w+(\\.\\w+)+') > 0;

-- space after each character: back-references are $1, not \1
SELECT REGEXP_REPLACE(country_name, '(.)', '$1 ') FROM employees;
```

Differences from Oracle (verified):
- **Case sensitivity follows the collation.** Under the default `utf8mb4_0900_ai_ci`, `REGEXP_LIKE('Abc', '^a')` = 1. Oracle is case-sensitive by default, so add the `'c'` match type (or `COLLATE utf8mb4_0900_as_cs`) to every converted pattern that relied on case. `'i'`, `'c'`, `'m'` (multiline), `'n'` (dot matches newline) and `'u'` (Unix line endings) are supported; **`'x'` is rejected** (error 1210) — remove whitespace/comments from the pattern.
- **Back-references in the replacement are `$1`.** `'\1 '` produces a literal `1` (verified: `REGEXP_REPLACE('Spain','(.)','\\1 ')` → `1 1 1 1 1`).
- **String-literal escaping:** backslashes in a MySQL string literal must be doubled (`'\\w'`), unless `NO_BACKSLASH_ESCAPES` is in `sql_mode`.
- `REGEXP_REPLACE(s, p, r, pos, occurrence, match_type)` and `REGEXP_SUBSTR(s, p, pos, occurrence)` take the same positional arguments as Oracle (verified: occurrence 2 → `aba`). `REGEXP_INSTR` has Oracle's `return_option`.
- A `BINARY` string argument combined with a `utf8mb4` pattern raises error 3995; compare as text with a case-sensitive collation instead.
- ICU supports `\w`, `\d`, `\s`, non-greedy `*?`, lookahead `(?=…)` and lookbehind `(?<=…)`; POSIX classes `[[:alpha:]]` also work.
- `regexp_time_limit` and `regexp_stack_limit` cap pattern evaluation; a catastrophic pattern fails with an error instead of running forever.

## Conversion notes

| Usage | Oracle | Aurora MySQL 3 / 8.4 |
|---|---|---|
| Match | `REGEXP_LIKE(first_name, '^Ste(v\|ph)en$')` | `REGEXP_LIKE(first_name, '^Ste(v\|ph)en$', 'c')` |
| Count occurrences | `REGEXP_COUNT(s, 'g', 3, 'c')` | `CHAR_LENGTH(x) - CHAR_LENGTH(REGEXP_REPLACE(x, 'g', '', 1, 0, 'c'))` for single-character patterns; a loop with `REGEXP_INSTR` for longer patterns |
| Position | `REGEXP_INSTR(email, '\w+@\w+(\.\w+)+')` | same, with doubled backslashes in the literal |
| Replace | `REGEXP_REPLACE(c, '(.)', '\1 ')` | `REGEXP_REPLACE(c, '(.)', '$1 ')` |
| Substring | `REGEXP_SUBSTR(s, p, pos, occ)` | same |

- Legacy (Aurora MySQL 5.7 only): just `REGEXP`/`RLIKE` (Henry Spencer library) and UDF-based replacement. Not needed on 3 / 8.4.
