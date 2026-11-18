<!-- dbmig questionnaire round=app pair=oracle-to-postgresql -->
# Application modernization questionnaire

Optional. It collects what a code scan cannot know about the application, so the
assistant asks fewer questions later. Answer each question on its `[Answer]:` line: the
option letter (for example `A`), or `X) <your own answer>`. Blank answers on questions
marked *(optional)* take the recommended option. Put your name on each section's
`[Answered by]:` line.

**Never write a password or connection value in this file**, only names of environment
variables or configuration keys.

When you are done, tell the assistant ("the application questionnaire is answered"), or
run `./dbmig questionnaire check --module app`. Nothing is edited because of this file:
the change plan still has to be approved first.

---

## Section 1 — Application

[Answered by]:

### Q1.1 Application directory (absolute path on the machine that runs the conversion)

_Example: /home/me/src/billing-service. The assistant never guesses this._

[Answer]:

### Q1.2 In-scope paths inside the application (blank = the whole application) *(optional)*

_Comma-separated, relative to the application directory. Example: src, pom.xml. Build output and dependencies (target/, bin/, obj/, node_modules/ …) are always excluded._

[Answer]:

### Q1.3 Other paths to leave untouched (blank = none) *(optional)*

_Generated code, vendored libraries, other teams' modules._

[Answer]:

### Q1.4 Application stack (blank = detect from the build files) *(optional)*

- A) Java (Spring Boot, JPA/Hibernate, MyBatis, JDBC)
- B) .NET (EF Core, Dapper, ADO.NET)
- C) Python (SQLAlchemy, Django, DB-API drivers)
- D) Node.js (Sequelize, TypeORM, Knex, raw driver)
- X) Other (describe)

[Answer]:

---

## Section 2 — Build and test

Validation builds and tests the converted application. Give the commands your team uses, so the assistant does not guess.

[Answered by]:

### Q2.1 Build command (blank = the stack's default, for example mvn -B clean package) *(optional)*

[Answer]:

### Q2.2 Test command (blank = the stack's default; "none" if there are no tests) *(optional)*

[Answer]:

### Q2.3 How the application finds its database (environment variables or config keys) *(optional)*

_Names only, never values or passwords. Example: DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD (from AWS Secrets Manager)._

[Answer]:

---

## Section 3 — Backup and change handling

[Answered by]:

### Q3.1 How should the original application be backed up before the first edit? *(optional)*

_git needs a clean working tree. When git cannot be used, the backup falls back to a file copy, so no file is edited without a backup._

- A) Use git when the application is in a clean git repository, else copy the files **(recommended)**
- B) Use git (falls back to a file copy when git cannot be used)
- C) Always copy the in-scope files into the migration workspace
- X) Other (describe)

[Answer]:

### Q3.2 Where should the edits go when the application is in git? *(optional)*

- A) Leave them uncommitted in the working tree for your review (the assistant never commits or pushes) **(recommended)**
- B) Create a new local branch dbmig/<project> before the first edit (still uncommitted; never pushed)
- X) Other (describe)

[Answer]:

---

## Section 4 — Conversion policies — all engine pairs

These answers set defaults for changes that repeat across many call sites. Leave a question blank to take the recommended option.

[Answered by]:

### Q4.1 Code that checks vendor error codes (ORA-xxxxx, SQL Server error numbers) *(optional)*

- A) Map each check to the target's error code or SQLSTATE **(recommended)**
- B) Switch to the framework's portable exceptions where it already offers them
- X) Other (describe)

[Answer]:

### Q4.2 Mark changed SQL in the code? *(optional)*

- A) No inline markers; the conversion log and app.diff record every change **(recommended)**
- B) Add a short comment at each changed statement
- X) Other (describe)

[Answer]:

---

## Section 5 — Conversion policies — Oracle to PostgreSQL application code

[Answered by]:

### Q5.1 Queries that compare text case-insensitively (UPPER(col) = UPPER(?), LIKE on mixed case) *(optional)*

- A) Keep them as written (UPPER/LOWER work the same on PostgreSQL) **(recommended)**
- B) Use ILIKE for LIKE comparisons that were wrapped in UPPER/LOWER
- X) Other (describe)

[Answer]:

### Q5.2 Code that relies on Oracle treating '' as NULL *(optional)*

- A) Follow the database migration's empty-string policy **(recommended)**
- B) Normalise '' to NULL in the application before writing
- X) Other (describe)

[Answer]:

### Q5.3 Explicit sequence calls in SQL (seq.NEXTVAL) *(optional)*

- A) Rewrite to nextval('seq') with the converted sequence name **(recommended)**
- B) Let the database generate the key (identity) and read it back with RETURNING
- X) Other (describe)

[Answer]:

---

## Section 6 — Reviewers

[Answered by]:

### Q6.1 Who approves the application gates? (blank = whoever runs the module) *(optional)*

[Answer]:
