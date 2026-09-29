> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# App cutover
Deploy the Npgsql build; connection from the Secrets Manager secret (host/port/user/password) +
`dbname` setting; `SearchPath=dbo`. Smoke: lower-case search, address book, admin inventory.
Risks: case-sensitive equality on non-citext columns (owner: app team); login NullReference (pre-existing).
