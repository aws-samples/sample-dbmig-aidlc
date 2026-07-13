# Conversion Functions (TO_CHAR / TO_NUMBER)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.conversionfunctions.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** N/A — MySQL doesn't support all functions; unsupported ones require manual creation.

## Oracle

Covers `TO_CHAR` and `TO_NUMBER`.

### TO_CHAR
Converts numbers, dates, and strings to a string using format models.

`TO_CHAR` with strings:
| Call | Result |
|---|---|
| `to_char('0972')` | 0972 |
| `to_char('0972','9999')` | 972 |
| `to_char('0972','$9999.99')` | $972.00 |
| `to_char('0972','$0009999.99')` | $972.00 |
| `to_char('0972.48','$9999.999')` | $972.480 |

`TO_CHAR` with numbers:
| Call | Result |
|---|---|
| `to_char(0972)` | 972 |
| `to_char(0972,'9999')` | 972 |
| `to_char(0972,'$9999.99')` | $972.00 |
| `to_char(0972,'$0009999.99')` | $0000972.00 |
| `to_char(0972.48,'$9999.999')` | $972.480 |

`TO_CHAR` with dates (selected format models):
| Call | Result | Description |
|---|---|---|
| `to_char(sysdate,'YYYY')` | 2013 | Year |
| `to_char(sysdate,'YY')` | 13 | Last two digits of year |
| `to_char(sysdate,'YEAR')` | TWENTY THIRTEEN | Year in words |
| `to_char(sysdate,'SYYYY')` | 2017 | S prefixes (-) for BC |
| `to_char(sysdate,'Y,YYY')` | 2017 | Year with comma |
| `to_char(sysdate,'MONTH')` | SEPTEMBER | Complete month |
| `to_char(sysdate,'MON')` | SEP | 3-letter month |
| `to_char(sysdate,'MM')` | 9 | Month of year |
| `to_char(sysdate,'W')` | 4 | Week of month |
| `to_char(sysdate,'WW')` | 36 | Week of year (1-53) |
| `to_char(sysdate,'DAY')` | SATURDAY | Name of day |
| `to_char(sysdate,'DD')` | 30 | Day number |
| `to_char(sysdate,'D')` | 7 | Day of week (1-7) |
| `to_char(sysdate,'DDD')` | 273 | Day of year (1-366) |
| `to_char(sysdate,'DY')` | SAT | Short day |
| `to_char(sysdate,'HH')` / `'HH12'` | 9 | Hour (1-12) |
| `to_char(sysdate,'HH24')` | 21 | Hour (24h) |
| `to_char(sysdate,'MI')` | 15 | Minute |
| `to_char(sysdate,'SS')` | 24 | Second |
| `to_char(sysdate,'SSSSS')` | 79100 | Seconds after midnight |
| `to_char(sysdate,'PM')`/`'AM'` | PM | AM/PM |
| `to_char(sysdate,'DL')` | Saturday, February 23, 2017 | Long date |
| `to_char(sysdate,'Q')` | 3 | Quarter (1-4) |

### TO_NUMBER
Converts `CHAR`, `VARCHAR2`, `NCHAR`, `NVARCHAR2`, `BINARY_FLOAT`, `BINARY_DOUBLE` to number; optional format model for the first four.

| Data | Format | Result |
|---|---|---|
| -1234567890 | `9999999999S` | '1234567890-' |
| 0 | `99.99` | ' .00' |
| 0.1 | `99.99` | ' .10' |
| -0.2 | `99.99` | ' -.20' |
| 123.456 | `999.999` | ' 123.456' |
| 123.456 | `FM999.009` | '123.456' |
| 123.456 | `9.9EEEE` | ' 1.2E+02' |
| 123.45 | `L999.99` | ' $123.45' |
| 123.45 | `FML999.99` | '$123.45' |
| 1234567890 | `9999999999S` | '1234567890+' |

```sql
select to_number('99999') from dual;  -- 99999
```

## MySQL

The page defers to [Single-Row and Aggregate Functions](single-row-and-aggregate-functions.md). MySQL equivalents:
- `TO_CHAR(number)` → `FORMAT(n, decimals)` (note: not a full equivalent).
- `TO_CHAR(date,...)` → `DATE_FORMAT(date, '%Y-%m-%d %H:%i:%s')` style format specifiers.
- `TO_NUMBER(str)` → `CAST(str AS UNSIGNED/DECIMAL)` or arithmetic coercion; no direct `TO_NUMBER`.
- `STR_TO_DATE(str, fmt)` for string→date.

```sql
SELECT FORMAT(972, 2);                       -- 972.00
SELECT DATE_FORMAT(SYSDATE(), '%Y-%m-%d');   -- date formatting
SELECT CAST('99999' AS UNSIGNED);            -- 99999
```

## Conversion notes
- MySQL has no single function matching Oracle's rich `TO_CHAR`/`TO_NUMBER` format models — map each format model to `DATE_FORMAT`/`FORMAT`/`CAST` equivalents.
- Oracle date format codes (`YYYY`, `MON`, `DD`, `HH24`, `MI`, `SS`, `Q`, `WW`, ...) must be translated to MySQL `DATE_FORMAT` specifiers (`%Y`, `%b`, `%d`, `%H`, `%i`, `%s`, etc.). No direct equivalents exist for `'YEAR'` (words), `'DL'` (long date), or quarter `'Q'` — implement manually.
- For currency/padding format models (`$9999.99`, `L999.99`, `FM`), use `FORMAT` + string manipulation or `CONCAT`.
