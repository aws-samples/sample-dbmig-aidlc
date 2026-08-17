---
name: app-modernization-validation
description: >
  VALIDATION & TESTING phase of the optional application-modernization module: compile the
  converted application, diagnose and fix the compile/test failures the database migration caused
  (result-set types, error codes, driver APIs, ORM mappings), run the test suite, and report what
  is verified versus unverified. Engine-agnostic. Invoked by app-modernization-orchestrator after
  app-modernization-construction. Produces
  migrations/<project>/05-application/03-validation/build-report.md.
---

# Application Modernization — Validation & Testing

The deliverable of application modernization is not edited code — it is edited code **plus
evidence that it builds and behaves**. This skill produces that evidence.

## Step 1 — Build

Use the build command recorded at intake. Capture output to a file rather than scrolling it:

```
# Maven
mvn -q -B clean compile          > /tmp/app-build.log 2>&1; echo "exit=$?"
# Gradle
./gradlew compileJava --console=plain > /tmp/app-build.log 2>&1; echo "exit=$?"
# .NET
dotnet build --nologo            > /tmp/app-build.log 2>&1; echo "exit=$?"
# Python (syntax + imports)
python -m compileall -q src      > /tmp/app-build.log 2>&1; echo "exit=$?"
# Node
npm run build --silent           > /tmp/app-build.log 2>&1; echo "exit=$?"
```

Then read the **errors**, not the whole log:
`grep -nE "ERROR|error:|BUILD FAILURE|error CS[0-9]+" /tmp/app-build.log | head -40`

Record the exact command and exit status. If the project cannot build for a reason unrelated to
the migration (missing toolchain, absent network, unavailable private repository), say so
explicitly and mark the result **UNVERIFIED** — never imply a build passed when it did not run.

## Step 2 — Fix migration-caused failures

These are expected. Fixing them is part of this module's job.

| Symptom | Cause | Fix |
|---|---|---|
| Java `incompatible types: long cannot be converted to int` / C# `CS0266 cannot implicitly convert type 'long' to 'int'` | `COUNT(*)` now returns `bigint` | widen to `long`/`Int64`, or cast in SQL |
| error-code logic still comparing source-engine numbers (`getErrorCode()`, `SqlException.Number`, `OracleException.Number`) | error identity changed | compare the target identity — JDBC `getSQLState()`, Npgsql `PostgresException.SqlState`, `MySqlException.Number` — against the contract's mapping |
| NuGet `NU1605 package downgrade` after a provider swap | new EF provider pins a newer EF floor | align ALL EF packages to the provider's floor |
| runtime `42P01 relation "Book" does not exist` from a pure-LINQ app | EF quotes PascalCase against a case-folded schema | the `OnModelCreating` lower-case fold (see the pair's app-sql-rules) |
| `column "x" does not exist` at runtime, compiles fine | identifier case folding | alias in SQL, or lower-case the lookup key |
| ORM `Unknown entity`/validation failure on startup | `@Table`/`@Column` quoted to the old case | unquote, or requote to the target case |
| `ClassNotFoundException` on the old driver | driver swapped in config but not in the build file | align dependency and driver class |
| `is not a procedure` / wrong call shape | routine became a function | `SELECT * FROM f(?)` instead of `{ call f(?) }` |
| `operator does not exist: … = character varying` | implicit coercion Oracle allowed | explicit `CAST` — and treat as data quality |
| `NullPointerException` on a concatenated string | NULL propagation in `\|\|` | `COALESCE(...,'')` |
| Test asserts a row count that is now off by the paging window | `ROWNUM`-before-sort vs `LIMIT`-after-sort | re-express the intent; this is behavioural, re-flag it |

Rules while fixing:
- Fix the **root cause**, not the symptom. Widening a variable to silence a type error is correct;
  casting a `long` down to `int` to keep a signature is not.
- Every fix is still subject to the backup policy — if a file was not previously backed up, back it
  up (mirrored tree) before editing.
- If a fix requires a decision beyond the approved plan, **stop and ask**.
- Re-run the build after each logical group of fixes; do not batch unrelated changes into one
  attempt. If the same error survives two fix attempts, stop and reconsider the diagnosis rather
  than trying a third variation.

## Step 3 — Tests

Run the existing suite (`mvn -q test`, `./gradlew test`, `dotnet test`, `pytest -q`, `npm test`).

- Tests needing a live database will fail without one. State that plainly and distinguish
  **failed** from **not run**.
- Where tests exist but do not cover the converted SQL, say so — a green suite that never
  exercises a converted query is not evidence about that query.
- Do not weaken, skip or delete a failing test to make the build green. If a test encodes
  source-database behaviour that legitimately changed, update it and flag the change as
  behavioural, with the reason.
- If the target database is reachable, the strongest cheap check for converted SQL is to `PREPARE`
  each statement against it — that validates syntax *and* that every identifier resolves. Do this
  read-only; never write to the target from this module.

## Step 4 — Report — `03-validation/build-report.md`

1. **Build**: command, exit status, before/after error counts.
2. **Fixes applied**: file, line, error, fix, and whether it was migration-caused or pre-existing.
3. **Tests**: command, passed/failed/skipped, and which converted sites are actually covered.
4. **Verification matrix** — per converted site, one of:
   `compiled` · `prepared against target` · `covered by test` · **`UNVERIFIED`** (with why).
5. **Remaining behavioural risks** with a named owner — these survive a green build by definition.
6. **Residual work**: deferred items, blocked items, tests that should exist but do not.

Be explicit about the limit of what a build proves: compilation shows the code is well-formed, not
that a converted query returns the same rows. Only the equivalence tests, a live `PREPARE`, or a
covering test do that.
