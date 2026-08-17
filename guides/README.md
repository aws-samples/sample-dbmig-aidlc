# Migration Guides

Step-by-step guides, **one per engine pair** (`<source>-to-<target>`). The framework is
engine-pluggable: the orchestration, the `dbmig` CLI, and the AI-DLC lifecycle are the same
for every pair — only the engine definition, the playbook references, and the source/target
drivers change.

## Available guides

| Engine pair | Source → Target | Guide | Status |
|---|---|---|---|
| `oracle-to-postgresql` | Oracle → PostgreSQL (Aurora PostgreSQL compatible) | [oracle-to-postgresql.md](oracle-to-postgresql.md) | Available |
| `oracle-to-mysql` | Oracle → MySQL (Aurora MySQL compatible) | [oracle-to-mysql.md](oracle-to-mysql.md) | Available |
| `sqlserver-to-postgresql` | SQL Server → PostgreSQL (Aurora PostgreSQL compatible) | [sqlserver-to-postgresql.md](sqlserver-to-postgresql.md) | Available |
| `sqlserver-to-mysql` | SQL Server → MySQL (Aurora MySQL compatible) | [sqlserver-to-mysql.md](sqlserver-to-mysql.md) | Available |

## Adding a guide for a new engine pair

The dbmig package uses a thin **engine adapter** pattern (`scripts/dbmig/engines/base.py`
defines `SourceEngine`/`TargetEngine`; `registry.py` maps engine names to adapters), so a new
pair needs no changes to the CLI, prompt builder, data migration, or reconciliation code.
When a new engine pair is added, it gets:

1. An engine adapter implementing `SourceEngine` and/or `TargetEngine` in
   `scripts/dbmig/engines/<engine>.py`, registered in `engines/registry.py` (`ENGINES`).
2. An engine definition under `engines/<source>-to-<target>/` (datatype map, checks).
3. A playbook reference skill under `skills/<source>-to-<target>-playbook/`.
4. An application-layer rules directory `engines/<source>-to-<target>/app/`
   (`app-config.yaml` + `app-sql-rules.md`) if the optional app-modernization module should
   support the pair — the app skills are engine-agnostic and need no changes.
5. A guide here at `guides/<source>-to-<target>.md`, added to the table above.

The lifecycle skills (`db-migration-orchestrator`, `-inception`, `-construction`,
`-validation`, `-operations`) and the `dbmig` commands do not change per pair — they call the
adapter interface resolved from the active connection engines.

## Maintenance note

The per-pair guides share a common workflow and differ only in engine-specific details
(connection block, schema/port values, datatype and dialect notes). The
**Oracle → PostgreSQL guide is the canonical reference** for the shared mechanics — the other
guides intentionally point back to its §5–§12 rather than duplicate them. When the workflow
changes (a new command, a changed phase, a new flag), update
`oracle-to-postgresql.md` first, then propagate any pair-specific deltas to the other guides.
Keep the shared sections thin in the non-canonical guides to avoid drift.

## After the database: converting the application (optional)

Each pair also ships **application-layer** conversion rules (`engines/<pair>/app/`) used by the
opt-in `app-modernization-orchestrator` skill — embedded SQL, driver/ORM configuration,
stored-routine call sites, error codes. It never starts automatically; ask explicitly, e.g.
*"convert my application to work with the migrated database"*.
