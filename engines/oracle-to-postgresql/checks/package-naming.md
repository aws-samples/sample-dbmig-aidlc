# Check: package-flattening naming conflicts

PostgreSQL has no packages, so each Oracle package subprogram is flattened to a
schema-level routine named `<package>_<subprogram>` (lower-cased). Joining with
an underscore is readable but **not injective** — because package and subprogram
names may themselves contain underscores, two different Oracle routines can
collapse onto the same PostgreSQL name.

`convert-code` runs this check automatically (Oracle source) using
`ALL_PROCEDURES`, and classifies each clash:

| Kind | Severity | Meaning |
|---|---|---|
| `collision` | high | Different Oracle routines flatten to the same name — **must** disambiguate. |
| `collision` (`involves_standalone`) | high | A package routine flattens onto an existing standalone function/procedure name. |
| `overload` | medium | One Oracle subprogram with several overloads shares one flattened name — OK in PostgreSQL **only** if the argument signatures differ; otherwise rename. |

## Examples

```
BOOK_PKG.GET_X       -> book_pkg_get_x
BOOK.PKG_GET_X       -> book_pkg_get_x     -- COLLISION (two distinct routines)

AUDIT.LOG            -> audit_log
(standalone) AUDIT_LOG -> audit_log         -- COLLISION (shadows standalone)
```

## What to do when flagged

`collision` items are written to `migrations/<project>/follow-up.yaml` (kind
`naming_conflict`). Resolve before relying on the converted code by either:

1. **Use a distinct separator** for the colliding objects — e.g. the AWS SCT
   style `<package>$<subprogram>` (`book_pkg$get_x`). `$` is a legal,
   non-leading PostgreSQL identifier character and is collision-resistant
   because it does not appear in normal Oracle names. The conflict disappears
   under `$` (the check supports a `separator` argument to confirm this).
2. **Rename** the converted PostgreSQL routine explicitly and update its call
   sites.
3. For `overload` items, confirm the PostgreSQL functions differ by argument
   signature (so they coexist as overloads), or rename.

The check only inspects routine names; it does not address package **state**
(package-level variables), which is a separate conversion concern.
