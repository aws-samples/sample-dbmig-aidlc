# Inventory — DEMO (Oracle 19c)

Source: `inventory-DEMO.yaml` (`dbmig inventory`); row counts by `COUNT(*)` (optimizer statistics are not gathered on this schema).

| Object type | Count |
|---|---|
| FUNCTION | 5 |
| INDEX | 30 |
| PACKAGE | 5 |
| PACKAGE BODY | 5 |
| PROCEDURE | 5 |
| SEQUENCE | 12 |
| TABLE | 14 |
| TRIGGER | 1 |

| Table | Rows |
|---|---|
| ADDRESSES | 3 |
| BOOKS | 56 |
| BOOKS_COVER | 56 |
| BOOK_TYPES | 3 |
| CONDITIONS | 4 |
| CUSTOMERS | 3 |
| GENRES | 8 |
| LISTINGS | 56 |
| ORDERS | 0 |
| ORDER_ITEMS | 0 |
| PASSWORD_RESET_TOKENS | 0 |
| PERSISTENT_LOGINS | 0 |
| PUBLISHERS | 10 |
| SHOPPING_CART_ITEMS | 0 |

Total rows: 199. Datatypes in use: NUMBER 52, VARCHAR2 44, TIMESTAMP(6) 21, DATE 5, BLOB 1.

Excluded engine-internal objects (not migrated): 4 tables, 3 indexes (Oracle Text `DR$`).

Decision item `fulltext_redesign:BOOKS.BOOKS_TEXT_IDX` — DEMO.BOOKS (BOOKS_TEXT_IDX, CTXSYS.CONTEXT): CTXSYS.CONTEXT index BOOKS_TEXT_IDX on BOOKS(SEARCH_TEXT) has no 1:1 target equivalent — choose a redesign (e.g. PostgreSQL tsvector + GIN, MySQL FULLTEXT); internal DR$ tables are excluded.  
App impact: rewrite application CONTAINS()/SCORE() queries on BOOKS.SEARCH_TEXT to the chosen target full-text expression, matching the index verbatim
