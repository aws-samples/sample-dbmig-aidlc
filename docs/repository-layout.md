# Repository layout

```
dbmig-aidlc/
├── skills/                              # the framework brain (Kiro skills)
│   ├── db-migration-orchestrator/       # ENTRY — interview + phase routing + gates
│   ├── db-migration-inception/          # assessment & planning
│   ├── db-migration-construction/       # schema + PL/SQL conversion
│   ├── db-migration-validation/         # data load + equivalence testing
│   ├── db-migration-operations/         # cutover, rollback, monitoring
│   ├── db-migration-dms-sc-ingest/      # ALT entry: import an existing AWS DMS SC project
│   ├── app-modernization-orchestrator/  # OPTIONAL app-code module — entry (opt-in, gated)
│   ├── app-modernization-inception/     #   Inception: scan + classify impacted app sites
│   ├── app-modernization-construction/  #   Construction: apply approved edits + mirrored backups
│   ├── app-modernization-validation/    #   Validation: compile, fix, test, verification matrix
│   ├── app-modernization-operations/    #   Operations: app cutover plan feeding the DB runbook
│   ├── oracle-to-postgresql-playbook/   # AWS playbook → granular references
│   ├── oracle-to-mysql-playbook/        # AWS playbook → granular references
│   ├── sqlserver-to-postgresql-playbook/ # AWS playbook → granular references
│   └── sqlserver-to-mysql-playbook/     # AWS playbook → granular references
├── engines/
│   ├── _common/                         # questionnaire.yaml (common intake questions)
│   ├── oracle-to-postgresql/            # engine.yaml, datatype-map.yaml, checks/, app/, questionnaire.yaml
│   ├── oracle-to-mysql/                 # engine.yaml, datatype-map.yaml, checks/, app/, questionnaire.yaml
│   ├── sqlserver-to-postgresql/         # engine.yaml, datatype-map.yaml, checks/, app/, questionnaire.yaml
│   └── sqlserver-to-mysql/              # engine.yaml, datatype-map.yaml, checks/, app/, questionnaire.yaml
├── scripts/
│   ├── dbmig/                           # the Python package (./dbmig), incl. review/ (review site)
│   ├── tests/                           # pytest suite
│   └── requirements.txt                 # pyyaml, oracledb, psycopg[binary], pymysql, python-tds
├── docs/                                # topic pages (this folder)
├── guides/                              # step-by-step guides, one per engine pair
├── templates/                           # connections + migration-config examples
├── sample-run-oracle-to-pg/             # sample run 1: converted purely by dbmig-aidlc (Oracle DEMO)
├── sample-run-sqlserver-to-pg/          # sample run 2: converted purely by dbmig-aidlc (SQL Server BobsUsedBookStore + .NET app)
├── sample-run-dms-sc-sqlserver-to-pg/   # sample run 3: CONTINUE from AWS DMS SC output (SQL Server AdventureWorks)
└── migrations/                          # per-run workspaces (git-ignored; holds artifacts)
```

## Sample runs

Three complete, real runs are archived for reference. All are masked (no real hosts or
credentials) and hold each phase's artifacts, including the gate records (`project.yaml`), so you
can see the workflow's output without database access. Build a review site for any of them with
`./dbmig review --dir <sample-folder> --open`.

- **[sample-run-oracle-to-pg/](../sample-run-oracle-to-pg/)** — Oracle `DEMO` **converted purely
  by dbmig-aidlc**, all four AI-DLC phases plus modernization of the Spring Boot / JPA app.
- **[sample-run-sqlserver-to-pg/](../sample-run-sqlserver-to-pg/)** — SQL Server
  `BobsUsedBookStore` converted from scratch plus the ASP.NET Core / EF Core app.
- **[sample-run-dms-sc-sqlserver-to-pg/](../sample-run-dms-sc-sqlserver-to-pg/)** — a run that
  **starts from AWS DMS Schema Conversion output** and works forward (SQL Server `AdventureWorks`
  `Person` + `HumanResources`: import → ACCEPT/VERIFY/MANUAL triage → `diff-target` reconciliation
  → MANUAL reconversion → secondary-object drop/load/restore → `compare` + equivalence tests →
  VERIFY sign-off).
