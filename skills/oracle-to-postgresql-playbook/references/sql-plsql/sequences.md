# Sequences

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.sequences.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation; only minor syntax differences for a few options)
**SCT automation:** Four-star automation level; SCT action code index → Sequences

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): per-session `CACHE` semantics, bigint `MAXVALUE` limit (verified), `NOCACHE` syntax error (verified), unlogged sequences, `uuidv7()` alternative to scalable sequences, `setval` semantics.

## Oracle

Sequences are independent objects that generate unique numeric identifiers (often PK values). The same sequence can feed multiple tables. Concurrent users may see gaps. Oracle 18c adds **scalable sequences** (`SCALE`/`NOSCALE`, with `EXTEND`/`NOEXTEND`) optimized for high concurrency.

Options: `INCREMENT BY` (default 1, can't be 0), `START WITH` (default 1), `MAXVALUE`/`NOMAXVALUE`, `MINVALUE`/`NOMINVALUE`, `CYCLE`/`NOCYCLE` (default NOCYCLE), `CACHE`/`NOCACHE` (default caches 20; CACHE min 2).

```sql
-- Create
CREATE SEQUENCE SEQ_EMP
START WITH 100
INCREMENT BY 1
MAXVALUE 99999999999
CACHE 20
NOCYCLE;

DROP SEQUENCE SEQ_EMP;
SELECT * FROM USER_SEQUENCES;

-- Use in INSERT
CREATE TABLE EMP_SEQ_TST (COL1 NUMBER PRIMARY KEY, COL2 VARCHAR2(30));
INSERT INTO EMP_SEQ_TST VALUES(SEQ_EMP.NEXTVAL, 'A');

SELECT SEQ_EMP.CURRVAL FROM DUAL;   -- current value
SELECT SEQ_EMP.NEXTVAL FROM DUAL;   -- increment
ALTER SEQUENCE SEQ_EMP MAXVALUE 1000000;

-- Scalable sequence (18c)
CREATE SEQUENCE scale_seq MINVALUE 1 MAXVALUE 9999999999 SCALE;
select scale_seq.nextval from dual;  -- e.g. 1010320001
```

Oracle 12c `DEFAULT` using sequence, `SESSION`/`GLOBAL` sequences, and `IDENTITY`:

```sql
CREATE TABLE SEQ_TST ( COL1 NUMBER DEFAULT SEQ_1.NEXTVAL PRIMARY KEY, COL2 VARCHAR(30));
CREATE SEQUENCE SESSION_SEQ SESSION;
CREATE SEQUENCE SESSION_SEQ GLOBAL;   -- global is default
```

## PostgreSQL

PostgreSQL sequences serve the same purpose and `CREATE SEQUENCE` is mostly Oracle-compatible. A sequence is owned by its creator. No native scalable-sequence feature (18c). For high-concurrency keys that must not be a hot spot, use `uuidv7()` (PG 18, time-ordered UUID) or increase `CACHE`.

Synopsis:

```sql
CREATE [ TEMPORARY | TEMP ] SEQUENCE [ IF NOT EXISTS ] name
[ AS data_type ]
[ INCREMENT [ BY ] increment ]
[ MINVALUE minvalue | NO MINVALUE ] [ MAXVALUE maxvalue | NO MAXVALUE ]
[ START [ WITH ] start ] [ CACHE cache ] [ [ NO ] CYCLE ]
[ OWNED BY { table_name.column_name | NONE } ]
```

Parameter notes:
- `TEMPORARY`/`TEMP` — session-scoped sequence, dropped at session end (maps to Oracle `SESSION` sequence).
- `IF NOT EXISTS`, `AS data_type` (PG 10+: `smallint`/`integer`/`bigint`(default)).
- `INCREMENT BY` default 1; `START WITH` default 1.
- `NOCACHE` is NOT supported (syntax error, verified); omitting `CACHE` = no pre-cache (equivalent to Oracle `NOCACHE`); min CACHE value is 1.
- **`CACHE` semantics differ:** Oracle caches per instance, while PostgreSQL caches **per session**. With `CACHE 20`, two sessions get interleaved blocks (1–20, 21–40, …), so values are not ordered by time across sessions, and unused cached values are lost at disconnect (gaps). Oracle's default is `CACHE 20`; PostgreSQL's is `1`. Keep `CACHE 1` unless sequence contention is measured.
- **Range:** PostgreSQL sequences are at most `bigint` (max 9223372036854775807). Oracle's default `MAXVALUE` of 28 nines fails (`out of range for type bigint`, verified). Drop `MAXVALUE` values above the bigint limit (use `NO MAXVALUE`).
- `UNLOGGED` sequences (PG 15+, verified) suit unlogged staging tables.
- `OWNED BY` associates sequence with a column (no Oracle equivalent); dropping such a sequence errors due to the association.

```sql
-- Create (identical except whitespace in NO CYCLE)
CREATE SEQUENCE SEQ_1 START WITH 100
INCREMENT BY 1 MAXVALUE 99999999999 CACHE 20 NO CYCLE;

DROP SEQUENCE SEQ_1;
SELECT * FROM INFORMATION_SCHEMA.SEQUENCES;   -- or \ds

-- Use in CREATE TABLE / INSERT
CREATE TABLE SEQ_TST (COL1 NUMERIC DEFAULT NEXTVAL('SEQ_1') PRIMARY KEY, COL2 VARCHAR(30));
INSERT INTO SEQ_TST (COL2) VALUES('A');

-- Associate with a column
CREATE SEQUENCE SEQ_1 START WITH 100 INCREMENT BY 1 OWNED BY SEQ_TST.COL1;

-- Functions
SELECT CURRVAL('SEQ_1');
SELECT NEXTVAL('SEQ_1');
SELECT SETVAL('SEQ_1', 200);
ALTER SEQUENCE SEQ_1 MAXVALUE 1000000;
```

> Permissions: `NEXTVAL` needs `USAGE`+`UPDATE`; `CURRVAL`/`LASTVAL` need `USAGE`+`SELECT`.

`SERIAL` family (`SMALLSERIAL`/`SERIAL`/`BIGSERIAL`) creates an implicit sequence + `NOT NULL`:

```sql
CREATE TABLE SERIAL_SEQ_TST(COL1 SERIAL PRIMARY KEY, COL2 VARCHAR(10));
-- implicit sequence: serial_seq_tst_col1_seq
```

## Summary

| Parameter/feature | PostgreSQL compatibility | Comments |
|---|---|---|
| Create sequence syntax | Full, minor differences | |
| `INCREMENT BY` / `START WITH` | Full | |
| `MAXVALUE`/`NOMAXVALUE` | Full | use `NO MAXVALUE` |
| `MINVALUE`/`NOMINVALUE` | Full | use `NO MINVALUE` |
| `CYCLE`/`NOCYCLE` | Full | use `NO CYCLE` |
| `CACHE`/`NOCACHE` | Partial | `NOCACHE` unsupported but default behavior identical; `CACHE` compatible |
| 12c default-via-sequence | Supported | `DEFAULT NEXTVAL('SEQ_1')` |
| 12c session/global | Supported | use `TEMPORARY` for session sequence |
| 12c identity columns | Supported | use `GENERATED … AS IDENTITY` (preferred over `SERIAL`) |
| `MAXVALUE` > 9.2e18 | Not supported | clamp to `NO MAXVALUE` (bigint) |
| `CACHE n` | Partial | per-session cache, not per-instance |

## Conversion notes

- Mechanical syntax rewrites: `NOMAXVALUE`→`NO MAXVALUE`, `NOMINVALUE`→`NO MINVALUE`, `NOCYCLE`→`NO CYCLE`, drop `NOCACHE` (default behavior matches).
- `seq.NEXTVAL`/`seq.CURRVAL` (Oracle dot syntax) → function calls `NEXTVAL('seq')`/`CURRVAL('seq')`. Also `SETVAL('seq', n)` exists in PG.
- Oracle 18c scalable sequences (`SCALE`) have no PG equivalent — redesign for high concurrency if needed.
- After data loads with explicit IDs, reset sequences with `SETVAL` to avoid duplicate-key errors. Use `setval('seq', n, false)` so the next `nextval` returns `n` (verified), or `setval('seq', max_id)` so it returns `max_id + 1`.
- Oracle 12c `DEFAULT seq.NEXTVAL` → `DEFAULT nextval('seq')`. When the sequence feeds a single column, an identity column is usually the cleaner target.
- Sequences used by several tables stay as standalone sequences (no `OWNED BY`).
