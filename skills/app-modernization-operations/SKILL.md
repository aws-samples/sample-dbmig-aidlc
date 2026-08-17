---
name: app-modernization-operations
description: >
  OPERATIONS & CUTOVER phase of the optional application-modernization module: plan how the
  converted application deploys together with the database cutover — artifact + configuration,
  ordering against the DB cutover runbook, rollback, and post-cutover checks. Engine-agnostic.
  Invoked by app-modernization-orchestrator after Validation is approved. Produces
  migrations/<project>/05-application/04-operations/app-cutover.md.
---

# Application Modernization — Operations & Cutover

The application and the database must cut over **together**: the DB cutover runbook
(`migrations/<project>/04-operations/cutover-runbook.md`) already treats the converted app build
as a precondition (its step 0.1) and switches connections mid-runbook. This phase produces the
app-side half of that contract.

## Inputs

- The approved Validation results (`03-validation/build-report.md`), including the open
  behavioural risks and anything `UNVERIFIED`.
- The conversion log (`02-construction/conversion-log.md`) — especially config/credential changes.
- The **database** cutover runbook and rollback plan under `migrations/<project>/04-operations/`.

## Write `04-operations/app-cutover.md` covering

1. **Deploy artifact + configuration** — which build/tag carries the converted code, and the
   target connection configuration. Secrets by reference (environment variable / secrets manager),
   never inline; name the variable the config now expects (e.g. `DB_PASSWORD`).
2. **Ordering against the DB runbook** — cite the exact runbook step that deploys the app, and
   state the hard constraint: the app must not start against the target before the post-data
   objects (FKs, triggers) and identity resets are applied.
3. **Rollback** — redeploying the previous build and repointing at the source database, plus the
   point after which that stops being clean (the DB rollback plan's point of no return). If the
   old build is gone, say so — that is itself a finding.
4. **Feature flags / dual-run**, if the app supports running against either engine; otherwise say
   plainly that the switch is atomic with the deploy.
5. **Post-cutover checks** — the app-level signals that prove the *converted code paths* work,
   not just that the app is up: the rewritten search returns hits, a converted routine call
   succeeds, an insert allocates an identity. Cross-reference the DB monitoring checklist rather
   than duplicating it.
6. **Open behavioural risks carried into production**, each with a named owner — these survive a
   green build by definition (search ranking differences, limit-vs-rownum semantics, date
   approximations).
7. **Deferred/blocked items** that ship unresolved (with the recorded decision), so the runbook
   reader knows what is intentionally incomplete.

## Gate

Present the plan and **stop: "Approve the application cutover plan?"** Cutover execution itself
is a production action — only proceed under explicit user direction, step by step, never
unattended.

## Safety

- This phase writes documentation only; it deploys nothing.
- Never echo secret values when describing configuration.
- If the DB migration has not itself passed its Operations gate, say so — the app cutover plan
  cannot be approved ahead of the database's.
