# Pre-flight — oracle-pg18-20261030

| Check | Result |
|---|---|
| Toolkit | `dbmig 0.2.0` in repo `.venv` (Python 3.13); drivers oracledb 26.1.0 (thin), psycopg 3.3.6 |
| Source | Oracle Database 19c Enterprise Edition (RDS) — connected |
| Target | Aurora PostgreSQL 18.6 (Serverless v2, private subnets, reached over Client VPN) — connected, `sslmode=require` |
| Target baseline | `engines/oracle-to-postgresql/engine.yaml` `target_baseline.verified_for: ["18"]` matches `target.version: 18.6` → no version caution in the shared context |
