<!-- dbmig questionnaire round=1 pair=sqlserver-to-mysql -->
# Migration questionnaire — round 1

Answer each question on its `[Answer]:` line: the option letter (for example `A`), or
`X) <your own answer>` for something else. Blank answers on questions marked *(optional)*
take the recommended option. Several people can fill in different sections; put your name
on the section's `[Answered by]:` line.

**Never write a password in this file.** Give the name of the environment variable or the
AWS Secrets Manager secret that holds it.

When you are done, tell the assistant ("the questionnaire is answered"), or run
`./dbmig questionnaire check`. Questions that are still missing or unclear are listed
back to you; nothing is applied until you confirm.

---

## Section 1 — Project and starting point

[Answered by]:

### Q1.1 Project name (the workspace folder under migrations/)

_Letters, digits, dot, dash and underscore. Example: billing-ora2pg-2026q4_

[Answer]:

### Q1.2 Where does this migration start?

- A) Fresh conversion from the source database (dbmig-aidlc converts the schema and code) **(recommended)**
- B) AWS DMS Schema Conversion (DMS SC) has already converted the schema and it is applied to the target
- X) Other (describe)

[Answer]:

---

## Section 2 — Engines

[Answered by]:

### Q2.1 Source engine

- A) Oracle (11.2 or later)
- B) SQL Server (2008 or later)
- X) Other (describe)

[Answer]: B

### Q2.2 Source version (blank = detect from the server) *(optional)*

_Example: 19c, 12.2, 2019. Oracle 11.2 needs Oracle Instant Client (thick mode)._

[Answer]:

### Q2.3 Target engine

- A) Amazon Aurora PostgreSQL / Amazon RDS for PostgreSQL **(recommended)**
- B) Amazon Aurora MySQL / Amazon RDS for MySQL
- X) Other (describe)

[Answer]: B

### Q2.4 Target engine version

_Example: 17.7 (PostgreSQL) or 8.0 (Aurora MySQL 3). Version-specific defaults depend on it._

[Answer]:

---

## Section 3 — Connections (no passwords in this file)

Never write a password here. Give the NAME of the environment variable that will hold it, and optionally the AWS Secrets Manager secret it comes from. The assistant reads the secret at run time and never writes the value to disk.

[Answered by]:

### Q3.1 Source host name or IP

[Answer]:

### Q3.2 Source port *(optional)*

[Answer]:

<!-- only when source_engine == sqlserver -->
### Q3.4 SQL Server database name

[Answer]:

### Q3.5 Source user (read-only is enough)

_See guides/database-users-and-permissions.md_

[Answer]:

### Q3.6 Environment variable NAME that holds the source password *(optional)*

[Answer]:

### Q3.7 AWS Secrets Manager secret for the source (name or ARN; blank = none) *(optional)*

[Answer]:

### Q3.8 Target endpoint (writer)

[Answer]:

### Q3.9 Target port *(optional)*

[Answer]:

### Q3.10 Target database name

[Answer]:

### Q3.11 Target user (read-write on the target schemas)

[Answer]:

### Q3.12 Environment variable NAME that holds the target password *(optional)*

[Answer]:

### Q3.13 AWS Secrets Manager secret for the target (name or ARN; blank = none) *(optional)*

[Answer]:

### Q3.14 AWS CLI profile and Region for those secrets (example: myprofile us-east-1; blank = no secrets) *(optional)*

[Answer]:

### Q3.15 Target TLS *(optional)*

- A) Encrypt (require); no certificate setup **(recommended)**
- B) Encrypt and verify the server certificate and host name (needs the RDS CA bundle)
- X) Other (describe)

[Answer]:

---

## Section 4 — Scope

[Answered by]:

### Q4.1 Source schemas to migrate (comma-separated)

_Oracle owners or SQL Server schemas, e.g. APP, BILLING_

[Answer]:

### Q4.2 Only these objects (LIKE patterns, comma-separated; blank = all) *(optional)*

[Answer]:

### Q4.3 Exclude these objects (LIKE patterns, e.g. %_TMP, %_BAK; blank = none) *(optional)*

[Answer]:

### Q4.4 Identifier case on the target *(optional)*

- A) Fold to lower case (no quoting needed in SQL) **(recommended)**
- B) Preserve source case (every identifier must be double-quoted)
- X) Other (describe)

[Answer]:

---

## Section 5 — Strategy and testing

[Answered by]:

### Q5.1 What should be migrated? *(optional)*

- A) Schema **(recommended)**
- B) Schema and code only (no data)
- C) Data only (the target schema exists)
- X) Other (describe)

[Answer]:

### Q5.2 How does test data reach the target? *(optional)*

- A) dbmig loads it (dev/test loader, sample or full) **(recommended)**
- B) We load it with AWS DMS (or another tool); dbmig tests what is loaded
- X) Other (describe)

[Answer]:

<!-- only when data_load != dms -->
### Q5.3 How much data should dbmig load for testing? *(optional)*

- A) A sample per table (sample_rows_per_table) **(recommended)**
- B) Every row (dev/test volumes only)
- X) Other (describe)

[Answer]:

### Q5.5 When a conversion or test fails during a run *(optional)*

- A) Log it to follow-up.yaml and continue; review at the gate **(recommended)**
- B) Stop and ask me each time
- X) Other (describe)

[Answer]:

---

## Section 6 — Governance

[Answered by]:

### Q6.1 Who approves the phase gates? (names; blank = whoever runs the migration) *(optional)*

[Answer]:

### Q6.2 Should dbmig refuse later-phase commands until the previous gate is approved? *(optional)*

- A) No, warn only **(recommended)**
- B) Yes, refuse (run.enforce_gates: true)
- X) Other (describe)

[Answer]:

---

## Section 7 — Conversion policies — SQL Server to MySQL

These answers set conversion defaults so fewer questions come up later. Leave a question blank to take the recommended option. Anything not covered here is still asked when it is found.

[Answered by]:

### Q7.1 SQL Server compares strings case-insensitively by default (_CI_ collations). On MySQL: *(optional)*

- A) Case-insensitive utf8mb4_0900_ai_ci (keeps the source behaviour) **(recommended)**
- B) Case-sensitive utf8mb4_0900_as_cs; the application adapts
- X) Other (describe)

[Answer]:

### Q7.2 datetime / datetime2 columns *(optional)*

- A) DATETIME(3) (datetime has ~3 ms precision) **(recommended)**
- B) DATETIME(6)
- X) Other (describe)

[Answer]:

### Q7.3 money / smallmoney columns *(optional)*

- A) DECIMAL(19,4) **(recommended)**
- X) Other (describe)

[Answer]:

### Q7.4 uniqueidentifier columns *(optional)*

- A) CHAR(36) (readable; simple) **(recommended)**
- B) BINARY(16) with UUID_TO_BIN / BIN_TO_UUID (compact; the load must convert the values — AWS DMS transformation or a custom load, not the dbmig dev loader)
- X) Other (describe)

[Answer]:

### Q7.5 Procedures that return result sets *(optional)*

- A) Keep them as procedures (MySQL procedures can return result sets) **(recommended)**
- X) Other (describe)

[Answer]:

### Q7.6 Cross-database references (OtherDb.dbo.Table) *(optional)*

- A) Separate MySQL databases on the same cluster (otherdb.table) **(recommended)**
- X) Other (describe)

[Answer]:

### Q7.7 SQL Server Agent jobs *(optional)*

- A) MySQL Event Scheduler (event_scheduler=ON in the parameter group) **(recommended)**
- B) External scheduler (for example Amazon EventBridge Scheduler)
- X) Other (describe)

[Answer]:
