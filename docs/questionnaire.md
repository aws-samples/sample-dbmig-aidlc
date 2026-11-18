# Two ways to start: conversation or questionnaire

By default the assistant asks for what it needs as the migration goes. Some teams prefer the
typical AI-DLC style instead: answer a **markdown questionnaire** up front (the DBA fills in the
connections, an architect the conversion policies) and get fewer questions later. Ask for it:

- *"Start an Oracle to PostgreSQL migration with a questionnaire."*

or set `intake.mode: questionnaire` in `migration-config.yaml`.

In conversational mode the assistant mentions the questionnaire once and does not wait for it.
A questionnaire that is already answered is always used, in either mode: the assistant asks
only about what is missing or unclear.

## Two rounds

1. **Round 1** (`migrations/<project>/00-intake/questionnaire.md`, or `./questionnaire.md` until
   the project is named): project, engines, connections (environment-variable or Secrets Manager
   names, **never passwords**), scope, strategy, and the engine pair's **conversion policies**
   (for example how `''` behaves, NUMBER mapping, package layout, full-text search, case-insensitive
   collations). Each question has lettered options, a recommended one and `X) Other`.
2. **Round 2** (`01-assessment/decisions-questionnaire.md`), only if needed: the decisions the
   assessment found that no round-1 policy answered. When every decision is already answered,
   there is no round 2.

Decisions that come up later in the run (for example a unit that still fails after the maximum
retries) are asked in chat.

## Examples

| File | What it shows |
|---|---|
| [round1-answered-oracle-to-postgresql.md](examples/questionnaire/round1-answered-oracle-to-postgresql.md) | an answered round 1 (masked): several people's sections, defaults left blank, one `X) Other` answer |
| [round2-answered-oracle-to-mysql.md](examples/questionnaire/round2-answered-oracle-to-mysql.md) | an answered round 2: one decision the assessment found (Oracle Text index → MySQL FULLTEXT) |
| Blank round 1 per pair: [Oracle → PostgreSQL](examples/questionnaire/round1-blank-oracle-to-postgresql.md), [Oracle → MySQL](examples/questionnaire/round1-blank-oracle-to-mysql.md), [SQL Server → PostgreSQL](examples/questionnaire/round1-blank-sqlserver-to-postgresql.md), [SQL Server → MySQL](examples/questionnaire/round1-blank-sqlserver-to-mysql.md) | exactly what `./dbmig questionnaire new --pair <pair>` writes, with each pair's conversion-policy section |

## Filling it in

Answer on each `[Answer]:` line with the option letter (`A`), or `X) <your own answer>`. A blank
answer on a question marked *(optional)* takes the recommended option. Several people can fill in
different sections; each section has an `[Answered by]:` line.

```markdown
### Q7.1 Oracle stores '' as NULL. How should empty strings behave on PostgreSQL? *(optional)*

- A) Keep Oracle behaviour: treat '' as NULL **(recommended)**
- B) Use PostgreSQL behaviour: '' and NULL are different
- X) Other (describe)

[Answer]: A
```

## Commands

```bash
./dbmig questionnaire new   --project P --pair oracle-to-postgresql   # round 1
./dbmig questionnaire check --project P                # missing / invalid / "Other" answers
./dbmig questionnaire check --project P --apply        # writes migration-config.yaml,
                                                       # connections.yaml (no passwords), policies
./dbmig questionnaire new   --project P --round 2      # after inventory, if decisions remain
./dbmig questionnaire check --project P --round 2 --apply
```

- `new` pre-fills answers from an existing `connections.yaml` / `migration-config.yaml` (never a
  password) and refuses to replace a file that already has answers (`--force` to start over).
- The first `check` may add questions that depend on the engines you chose (the pair's policies,
  the Oracle service name or SQL Server database). Your answers are kept.
- `check` never interprets free text: "Other" answers are listed for the assistant to clarify
  with you.
- `--apply` does not overwrite existing values in `migration-config.yaml` or `connections.yaml`
  without `--overwrite`; it lists the differences first (password fields masked).

## What the answers do

- Settings go to `migration-config.yaml`, connection fields to `connections.yaml` (passwords as
  `${VAR}` references), and policies to `migrations/<project>/project.yaml`.
- Policies **answer later decisions automatically** (recorded `via: questionnaire`, with a link to
  the answer), and are injected at the top of the conversion and test context, with the same
  precedence as customer-specific rules.
- If the database contradicts an answer, the decision stays open and the assistant asks.
- Policies never approve a gate. Changing an answer after the inception gate was approved makes
  that gate stale (see [Gates, decisions and the review site](gates-and-review.md)).

Questions live in `engines/_common/questionnaire.yaml` (common) and
`engines/<pair>/questionnaire.yaml` (per-pair policies), so a new engine pair needs no code change.

## Application questionnaire

The optional [application modernization](application-modernization.md) module has its own
questionnaire, for the application team. It has **one round**: the application's open questions
come up in the change plan, which is approved at the `app-inception` gate anyway.

```bash
./dbmig questionnaire new   --module app --project P      # 05-application/00-intake/app-questionnaire.md
./dbmig questionnaire check --module app --project P [--apply]
```

It asks for the application directory and scope, build and test commands, how the application
finds its database (names only, never values), the backup mode (`auto`: git when possible, else a
file copy) and where edits go in git, plus conversion policies that repeat across many call sites.
`--apply` stores the answers in `project.yaml` under `app:` (never in the database policies, so no
database gate goes stale) and writes `05-application/00-intake/app-policies.md` for the
application skills. Changing an application answer after approval makes `app-inception` stale.

Questions live in `engines/_common/app-questionnaire.yaml` and `engines/<pair>/app/questionnaire.yaml`.

| File | What it shows |
|---|---|
| [app-answered-oracle-to-postgresql.md](examples/questionnaire/app-answered-oracle-to-postgresql.md) | an answered application questionnaire (masked), with one `X) Other` answer |
| [app-blank-oracle-to-postgresql.md](examples/questionnaire/app-blank-oracle-to-postgresql.md) | exactly what `./dbmig questionnaire new --module app --pair oracle-to-postgresql` writes |
