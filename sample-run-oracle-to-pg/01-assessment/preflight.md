# Pre-flight — DEMO (Oracle → Aurora PostgreSQL)

- **Deps:** `scripts/requirements.txt` installed (oracledb thin, psycopg3, pymysql, python-tds, pyyaml).
- **Connectivity (`dbmig test-connection --side both`):** PASS
  - Source: `oracle://admin@oracle-source.example.com:1521/ORCL` — Oracle 19c Enterprise Edition.
  - Target: `postgresql://postgres@aurora-cluster.example.com:5432/demodb` — **Aurora PostgreSQL 17.7**.
- Connection via Python drivers only (no native client tools). Secrets injected from git-ignored `.env`.
