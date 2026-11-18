# dbmig-aidlc documentation

Start with the [README](../README.md), then pick the page for what you are doing.

## Paths

| Page | Read it when |
|---|---|
| [Step-by-step guides](../guides/README.md) | you run a migration for one engine pair (Oracle or SQL Server → PostgreSQL or MySQL) |
| [Continue from AWS DMS Schema Conversion](dms-sc-continuation.md) | DMS SC already converted and applied the schema |
| [Application modernization](application-modernization.md) | the application must work with the migrated database |

## Topics

| Page | Covers |
|---|---|
| [Conversation or questionnaire](questionnaire.md) | the optional two-round markdown questionnaire |
| [Gates, decisions and the review site](gates-and-review.md) | recorded approvals, stale gates, decisions, `./dbmig review` |
| [How conversion works](how-conversion-works.md) | the Kiro conversion hand-off, the full CLI pipeline, failures and retries |
| [Connecting to databases](connections.md) | Python drivers, the connections file, AWS Secrets Manager |
| [Database users and permissions](../guides/database-users-and-permissions.md) | least-privilege source and target users |
| [Run workspaces](workspaces.md) | `--project`, multiple runs, the workspace layout |
| [Repository layout](repository-layout.md) | what is where, and the archived sample runs |

## Design

| Page | Covers |
|---|---|
| [ARCHITECTURE.md](../ARCHITECTURE.md) | skills and toolkit layers, engine adapters, data flow, security |
| [DB-MIGRATION-AIDLC.md](../DB-MIGRATION-AIDLC.md) | how the framework maps to the AI-Driven Development Life Cycle |
