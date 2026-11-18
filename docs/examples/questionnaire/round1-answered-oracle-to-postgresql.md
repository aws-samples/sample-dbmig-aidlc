<!-- dbmig questionnaire round=1 pair=oracle-to-postgresql -->
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

[Answered by]: Alex (migration lead)

### Q1.1 Project name (the workspace folder under migrations/)

_Letters, digits, dot, dash and underscore. Example: billing-ora2pg-2026q4_

[Answer]: billing-ora2pg

### Q1.2 Where does this migration start?

- A) Fresh conversion from the source database (dbmig-aidlc converts the schema and code) **(recommended)**
- B) AWS DMS Schema Conversion (DMS SC) has already converted the schema and it is applied to the target
- X) Other (describe)

[Answer]: A

---

## Section 2 — Engines

[Answered by]:

### Q2.1 Source engine

- A) Oracle (11.2 or later)
- B) SQL Server (2008 or later)
- X) Other (describe)

[Answer]: A

### Q2.2 Source version (blank = detect from the server) *(optional)*

_Example: 19c, 12.2, 2019. Oracle 11.2 needs Oracle Instant Client (thick mode)._

[Answer]: 19c

### Q2.3 Target engine

- A) Amazon Aurora PostgreSQL / Amazon RDS for PostgreSQL **(recommended)**
- B) Amazon Aurora MySQL / Amazon RDS for MySQL
- X) Other (describe)

[Answer]: A

### Q2.4 Target engine version

_Example: 17.7 (PostgreSQL) or 8.0 (Aurora MySQL 3). Version-specific defaults depend on it._

[Answer]: 17.7

---

## Section 3 — Connections (no passwords in this file)

Never write a password here. Give the NAME of the environment variable that will hold it, and optionally the AWS Secrets Manager secret it comes from. The assistant reads the secret at run time and never writes the value to disk.

[Answered by]: Sam (DBA)

### Q3.1 Source host name or IP

[Answer]: oracle.example.internal

### Q3.2 Source port *(optional)*

[Answer]:

<!-- only when source_engine == oracle -->
### Q3.3 Oracle service name (or SID, prefixed with "sid:")

_Example: ORCLPDB1, or sid:ORCL_

[Answer]: ORCL

### Q3.5 Source user (read-only is enough)

_See guides/database-users-and-permissions.md_

[Answer]: dbmig_reader

### Q3.6 Environment variable NAME that holds the source password *(optional)*

[Answer]: ORA_PASSWORD

### Q3.7 AWS Secrets Manager secret for the source (name or ARN; blank = none) *(optional)*

[Answer]: prod-migration/oracle-source

### Q3.8 Target endpoint (writer)

[Answer]: app-db.cluster-example.us-east-1.rds.amazonaws.com

### Q3.9 Target port *(optional)*

[Answer]:

### Q3.10 Target database name

[Answer]: billing

### Q3.11 Target user (read-write on the target schemas)

[Answer]: app_owner

### Q3.12 Environment variable NAME that holds the target password *(optional)*

[Answer]: PG_PASSWORD

### Q3.13 AWS Secrets Manager secret for the target (name or ARN; blank = none) *(optional)*

[Answer]: prod-migration/aurora-target

### Q3.14 AWS CLI profile and Region for those secrets (example: myprofile us-east-1; blank = no secrets) *(optional)*

[Answer]: migration-ro us-east-1

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

[Answer]: BILLING

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

[Answer]: B

<!-- only when data_load != dms and target_engine == postgresql -->
### Q5.4 How should dbmig move the data? *(optional)*

- A) Through the machine running dbmig (simplest) **(recommended)**
- B) Target reads the source directly via oracle_fdw / tds_fdw (fast across a slow VPN)
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

[Answer]: Alex, Priya

### Q6.2 Should dbmig refuse later-phase commands until the previous gate is approved? *(optional)*

- A) No, warn only **(recommended)**
- B) Yes, refuse (run.enforce_gates: true)
- X) Other (describe)

[Answer]:

---

## Section 7 — Conversion policies — Oracle to PostgreSQL

These answers set conversion defaults so fewer questions come up later. Leave a question blank to take the recommended option. Anything not covered here is still asked when it is found.

[Answered by]: App architect

### Q7.1 Oracle stores '' as NULL. How should empty strings behave on PostgreSQL? *(optional)*

- A) Keep Oracle behaviour: treat '' as NULL **(recommended)**
- B) Use PostgreSQL behaviour: '' and NULL are different
- X) Other (describe)

[Answer]: A

### Q7.2 Columns declared NUMBER without precision *(optional)*

- A) numeric (exact, safe) **(recommended)**
- B) bigint when the column only holds integers (keys, counters); numeric otherwise
- X) Other (describe)

[Answer]:

### Q7.3 Oracle DATE (always carries a time part) *(optional)*

- A) timestamp(0) — keeps the time part **(recommended)**
- B) date — the application never stores a time part
- X) Other (describe)

[Answer]:

### Q7.4 PL/SQL packages *(optional)*

- A) One PostgreSQL schema per package (pkg.routine keeps its name) **(recommended)**
- B) Flatten to pkg_routine in the main schema
- X) Other (describe)

[Answer]: A

### Q7.5 PRAGMA AUTONOMOUS_TRANSACTION (e.g. error logging) *(optional)*

- A) dblink to the same database (needs the dblink extension) **(recommended)**
- B) Redesign: let the caller commit; log through a separate connection in the application
- X) Other (describe)

[Answer]:

### Q7.6 Database links (table@dblink) *(optional)*

- A) Foreign tables (oracle_fdw / postgres_fdw) **(recommended)**
- B) Out of scope; the application reaches the remote system
- X) Other (describe)

[Answer]: X) We have no database links in this schema

### Q7.7 DBMS_SCHEDULER / DBMS_JOB jobs *(optional)*

- A) pg_cron in the target database **(recommended)**
- B) External scheduler (for example Amazon EventBridge Scheduler)
- X) Other (describe)

[Answer]:

### Q7.8 Oracle Text (CONTEXT / CTXCAT indexes), if any *(optional)*

- A) PostgreSQL full-text search (tsvector + GIN) **(recommended)**
- B) Substring search with pg_trgm
- C) Move search to an external engine (for example Amazon OpenSearch Service)
- D) Not used, or decide when it is found
- X) Other (describe)

[Answer]: A

### Q7.9 Compatibility extensions (aws_oracle_ext, orafce) *(optional)*

- A) Native PostgreSQL only; no compatibility extension **(recommended)**
- B) orafce is allowed where it saves rewriting (Oracle-like functions)
- X) Other (describe)

[Answer]:

### Q7.10 Sequences filled by BEFORE INSERT triggers *(optional)*

- A) Identity columns where the sequence serves one table **(recommended)**
- B) Keep every sequence and use DEFAULT nextval(...)
- X) Other (describe)

[Answer]:

### Q7.11 CHAR(n) columns *(optional)*

- A) Keep char(n) **(recommended)**
- B) varchar(n) — trailing blanks are not meaningful
- X) Other (describe)

[Answer]:
