# Application modernization (separate, opt-in module)

After a database migration, the **application** still speaks the old dialect — embedded SQL,
datasource/ORM configuration, stored-routine call sites, error codes, result-set typing. An
optional module converts the application to match, driven by the migration's own artifacts
(its conversion log and validation carry-forwards) rather than generic rules.

**Like-for-like only.** The application keeps its architecture, framework and behaviour — the
module changes only what the database migration invalidated. It is *not* application refactoring:
no monolith-to-microservices decomposition, framework/language upgrades, ORM swaps, or general
cleanup — those are separate engagements.

- **Opt-in only — it never starts automatically.** Ask for it explicitly, e.g. *"convert my
  application to work with the migrated database"*. The `app-modernization-orchestrator` skill
  then asks for the application directory and which `migrations/<project>/` workspace to conform to.
- **Same AI-DLC phases, same gates**: Inception (inventory + **change plan**) → Construction →
  Validation (build/test) → Operations (app cutover). **Nothing is edited before the change plan
  is approved** — every proposed edit is previewed per site (current vs proposed code, risk class).
- **Backups are a mirrored tree**, `migrations/<project>/05-application/backup/<timestamp>/…`,
  never `.bak` files scattered beside the originals.
- **Engine-pair extensible**: per-pair app rules live in `engines/<pair>/app/`
  (`app-config.yaml` + `app-sql-rules.md`), so new pairs need no skill changes. All four current
  pairs ship with app rules.

`./dbmig app-scan --app-dir <dir> --project <P>` is the read-only pre-scan the Inception phase
uses: dialect SQL sites, routine calls, configuration, and an entity ↔ target column type
cross-check.

Two archived runs include the application step:
[`sample-run-oracle-to-pg/05-application/`](../sample-run-oracle-to-pg/05-application/) (Spring
Boot / JPA) and [`sample-run-sqlserver-to-pg/05-application/`](../sample-run-sqlserver-to-pg/05-application/)
(ASP.NET Core / EF Core).
