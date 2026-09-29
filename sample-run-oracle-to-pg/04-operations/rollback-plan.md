> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# Rollback plan

- **Point of no return:** first application write accepted by Aurora (step 7). Before it, roll back by
  re-pointing the app at Oracle (previous build + Oracle datasource) — no data divergence.
- **After it:** writes exist only on Aurora. Either keep DMS reverse replication (PG → Oracle) running
  from cutover, or export rows created after cutover (`created_on > <cutover ts>` on orders,
  order_items, listings, customers, shopping_cart_items, password_reset_tokens) and replay them.
  Identity values issued on Aurora must not collide on Oracle — advance Oracle identities past Aurora MAX.
- Keep the Oracle source intact and reachable for a 14-day soak.
- Triggers: any 5xx on the smoke paths, `ddl-auto=validate` failure, reconcile mismatch, error rate > 2× baseline.
