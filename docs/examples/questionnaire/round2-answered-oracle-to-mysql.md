<!-- dbmig questionnaire round=2 -->
# Migration questionnaire — round 2 (billing-ora2my)

The assessment found these decisions that your round-1 answers did not cover. Answer each on its `[Answer]:` line with the option letter, or `X) <your own answer>`. Then tell the assistant, or run `./dbmig questionnaire check --round 2`.

## Section D — Decisions

[Answered by]: App architect

---

### D-001 How should the Oracle Text (CONTEXT/CTXCAT) index be redesigned on MySQL?

Kind: `fulltext_redesign` · Objects: BILLING.CUSTOMERS

_CTXSYS.CONTEXT index IX_CUSTOMERS_BIO_TXT on CUSTOMERS(BIO) has no 1:1 target equivalent — choose a redesign (e.g. PostgreSQL tsvector + GIN, MySQL FULLTEXT); internal DR$ tables are excluded. App impact: rewrite application CONTAINS()/SCORE() queries on CUSTOMERS.BIO to the chosen target full-text expression, matching the index verbatim_

- A) MySQL FULLTEXT index (InnoDB) with MATCH ... AGAINST **(recommended)**
- B) Move search to an external engine (e.g. Amazon OpenSearch Service); drop the index from the migration
- C) Drop the index; the application no longer needs it
- X) Other (describe)

[Answer]: A
