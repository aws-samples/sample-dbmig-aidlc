# Check: package-flattening naming conflicts

MySQL has no packages, so each Oracle package subprogram is flattened to a
schema-level routine named `<package>_<subprogram>` (lower-cased; in MySQL a
"schema" is a database, and routines are referenced as `` `db`.`routine` ``).
Joining with an underscore is readable but **not injective** — because package
and subprogram names may themselves contain underscores, two different Oracle
routines can collapse onto the same MySQL name.

`convert-code` runs this check automatically (Oracle source) using
`ALL_PROCEDURES`, and classifies each clash:

| Kind | Severity | Meaning |
|---|---|---|
| `collision` | high | Different Oracle routines flatten to the same name — **must** disambiguate. |
| `collision` (`involves_standalone`) | high | A package routine flattens onto an existing standalone function/procedure name. |
| `overload` | **high (MySQL)** | One Oracle subprogram with several overloads shares one flattened name. **MySQL does not support routine overloading** — same-named functions/procedures cannot coexist in a database even with different argument signatures — so every overload **must** be renamed. |

> **Difference from PostgreSQL:** on a PostgreSQL target, overloaded routines can
> coexist as long as their argument signatures differ, so `overload` is only a
> medium concern. On MySQL there is no signature-based overloading at all, so each
> overloaded Oracle subprogram needs its own distinct routine name.

## Examples

```
BOOK_PKG.GET_X       -> book_pkg_get_x
BOOK.PKG_GET_X       -> book_pkg_get_x     -- COLLISION (two distinct routines)

AUDIT.LOG            -> audit_log
(standalone) AUDIT_LOG -> audit_log         -- COLLISION (shadows standalone)

CALC_PKG.TOTAL(n NUMBER)          -> calc_pkg_total
CALC_PKG.TOTAL(n NUMBER, c CHAR)  -> calc_pkg_total   -- OVERLOAD: illegal in MySQL,
                                                      --   rename one (e.g. _total_2)
```

## What to do when flagged

`collision` and `overload` items are written to
`migrations/<project>/follow-up.yaml` (kind `naming_conflict`). Resolve before
relying on the converted code by either:

1. **Use a distinct separator** for the colliding objects — e.g. the AWS SCT
   style `<package>$<subprogram>` (`book_pkg$get_x`). `$` is a legal MySQL
   identifier character and is collision-resistant because it does not appear in
   normal Oracle names. The conflict disappears under `$` (the check supports a
   `separator` argument to confirm this).
2. **Rename** the converted MySQL routine explicitly and update its call sites.
3. For `overload` items, **rename each overload to a unique routine name** (MySQL
   cannot distinguish them by signature) — e.g. append a numeric suffix or the
   distinguishing argument, and update callers accordingly.

The check only inspects routine names; it does not address package **state**
(package-level variables), which is a separate conversion concern.
