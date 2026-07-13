---
name: db-migration-inception
description: Inception phase (assessment & planning) of an AI-DLC database migration. Use after the orchestrator has gathered intake and verified connectivity, or when the user asks to assess, scope, or plan a database migration. Engine-agnostic across all supported pairs (Oracle or SQL Server → PostgreSQL or MySQL). Verifies connectivity, inventories the source schema objects, assesses source→target compatibility against the active pair's playbook, estimates effort/risk, and produces a migration plan. Writes artifacts to migrations/<project>/01-assessment/ and stops at a human approval gate.
---

# Inception — Assessment & Planning

This is the **Inception** phase. Output is an assessment and a migration plan the human
approves before any conversion happens. Mirrors AI-DLC Inception: gather requirements,
analyze, propose a plan, stop for approval.

## Active engine pair
Determine the pair from the connection engines: `<source>-to-<target>` (e.g.
`oracle-to-postgresql`, `sqlserver-to-mysql`). Substitute it for `<pair>` below — the engine
definition is `engines/<pair>/` and the knowledge base is `skills/<pair>-playbook/`.

## Inputs
- `connections.yaml`, `migration-config.yaml` (resolved by the orchestrator)
- Active engine pair definition `engines/<pair>/engine.yaml`
- Playbook reference skill `<pair>-playbook` for compatibility lookups

## Steps

### 1. Re-verify pre-flight (idempotent)
Ensure package deps are installed (`pip install -r scripts/requirements.txt`), then run
`python -m dbmig test-connection --side both`. Record driver versions and connectivity
status into `01-assessment/preflight.md`. Stop if it fails. (No native client tools are
used — connectivity is via Python drivers.)

### 2. Inventory the source
For each schema in `migration-config.yaml scope.schemas`, run:
```bash
python -m dbmig inventory --schema <SCHEMA> --project <project>
```
This writes structured `01-assessment/inventory.yaml` and `inventory.json` (object counts,
tables + row counts, datatypes in use, stored-code volume). Summarize it into a clean
`01-assessment/inventory.md` table.

### 3. Compatibility assessment
For each object type and notable construct found, consult the active pair's playbook
references (`skills/<pair>-playbook/references/...`) and classify each item:

| Category | Meaning |
|---|---|
| **Automatic** | Direct equivalent; low risk (most tables, standard types, basic DML) |
| **Assisted** | Mechanical rewrite with a known pattern |
| **Manual** | Needs redesign / human judgment |
| **Blocked** | No supported path yet; flag for the user (source-only features) |

Use `engines/<pair>/datatype-map.yaml` for datatype risk and the pair's SQL/code references
for construct-level guidance (each topic file carries a conversion category). Cite the
specific reference file per finding so it traces to guidance.

### 4. Effort & risk
Summarize: object counts by category, stored-code line counts, top risks, and the known
semantic differences that will need explicit testing for this pair — see
`engines/<pair>/checks/equivalence-spec.md` (e.g. empty-string/NULL, date arithmetic,
numeric rounding, case sensitivity, IDENTITY/sequence handling).

### 5. Migration plan
Write `01-assessment/migration-plan.md` with:
- Scope (schemas/objects in and out).
- Conversion order (tables → constraints/indexes → sequences → views → functions →
  procedures/packages → triggers), grouped into **units of work** that can be converted and
  tested independently (AI-DLC parallel construction principle).
- Testing approach: data path (`framework` vs `dms`), and which equivalence checks apply.
- Cutover approach (high level; detailed in Operations).
- Open questions / decisions needed from the user.

## Gate
Present `migration-plan.md` and the compatibility summary. **Stop and ask the orchestrator's
gate question: "Approve the assessment & migration plan?"** Do not start conversion. If the
user wants changes (scope, ordering, strategy), revise the plan and re-present.

## Notes
- Read-only on the source. This phase must not modify the source or target.
- Be honest about Blocked/Manual items — surfacing them now is the point of Inception.
