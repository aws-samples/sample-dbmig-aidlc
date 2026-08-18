# Inventory — DEMO schema (Oracle 19c)

## Object counts (raw)
| Object | Count |
|---|---|
| Tables | 18 (raw) → **14 user tables** (4 are Oracle Text `DR$BOOKS_TEXT_IDX$*` internals) |
| Indexes | 33 → 31 NORMAL, 1 DOMAIN (Oracle Text), 1 IOT-TOP; **16 are system-named** (`SYS_*`) |
| Sequences | 12 (all back IDENTITY columns) |
| Views | 0 |
| Functions | 5 |
| Procedures | 5 |
| Packages | 5 (+ 5 package bodies) |
| Triggers | 1 (`TRG_BOOK_SEARCH_TEXT` — maintains Oracle Text search column) |

## User tables + live row counts (full-load sizing)
| Table | Rows |
|---|---|
| ADDRESSES | 3 |
| BOOKS | 56 |
| BOOKS_COVER | 56 (has `COVER_IMAGE BLOB`) |
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
| **TOTAL** | **199 rows / 14 tables** |

## Datatypes in use (user tables)
`NUMBER`, `VARCHAR2`, `TIMESTAMP(6)`, `DATE`, `BLOB` (1: `BOOKS_COVER.COVER_IMAGE`).
> Note: the `ROWID`(2) and `CHAR`(1) reported in the raw datatype scan belong to the Oracle Text
> `DR$*` internal tables, **not** user tables — no user-table ROWID dependency exists.

## Identity columns
12 tables use an Oracle `GENERATED … AS IDENTITY` `ID` column (integer surrogate PKs).

## Stored code
5 packages (ORDER_PKG, BOOK_PKG, INVENTORY_PKG, REPORTING_PKG, VALIDATION_PKG), 5 standalone
procedures, 5 standalone functions, 1 trigger. Largest body: `ORDER_PKG` (70 lines). Total PL/SQL ≈ 450 lines.

## Cross-schema dependencies
None.
