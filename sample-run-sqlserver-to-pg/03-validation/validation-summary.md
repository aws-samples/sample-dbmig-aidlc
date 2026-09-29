# Validation summary — dbo → dbo

| Check | Result |
|---|---|
| Data load | 2,963 rows, 20 tables |
| Reconcile | **20/20** match |
| Equivalence tests | **68/68** (56/68 first run → 3 defects fixed → 68/68; 12 follow-ups auto-resolved) |
| Identity | 14/14 safe |

**LOW_COVERAGE:** `usplogerror` (ErrorLog empty); `uspgettopregion` date-relative (the 6-month window is
empty today on both engines). **Manual review:** `vwopencoupons` (`CURRENT_USER` semantics); raised-error
paths are not compared by the harness.
