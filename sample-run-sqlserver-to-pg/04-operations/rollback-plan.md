> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# Rollback plan
Before the first write on Aurora: redeploy the previous build (SQL Server provider). After: DMS reverse
replication or replay rows created after cutover (`createdon > <ts>` on order, orderitem, offer, address,
shoppingcart*). Keep SQL Server reachable for 14 days.
