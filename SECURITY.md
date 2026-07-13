# Security

This is reference/sample tooling for database migration, intended for development and testing
purposes only. **Test everything in a non-production environment first**, and independently review
and harden it for your own quality and security standards before you deploy it anywhere (see
`DISCLAIMER.txt`).

## Secrets and sample data

- **No credentials are committed.** `connections.yaml` / `migration-config.yaml` are git-ignored;
  the `sample_*` copies use `${ENV}` placeholders and masked endpoints. Passwords are read from
  environment variables at run time, and an unset variable produces a warning rather than a silent
  empty value.
- **Sample data is synthetic.** The captured sample runs use reserved documentation values only
  (`example.com` email domains, `555-01xx` phone numbers). When the toolkit samples real source rows
  to ground test generation, values from sensitive-named columns (passwords, hashes, salts, tokens,
  keys) are redacted before they are written to any prompt file.

## Encryption in transit

Transport encryption is **secure by default in the code** (not just the docs), split by role:

**Targets — PostgreSQL / MySQL (Aurora/RDS).** The connection `sslmode` defaults to **`require`**
(in both the `Connection` dataclass and the config fallback), so the target connection opens an
**encrypted channel with no silent plaintext fallback**. Aurora/RDS serve TLS by default, so this
works with no certificate management. Modes:

- `require` (default) — encrypt; do not fall back to clear text. No CA needed.
- `verify-ca` / `verify-full` — additionally **authenticate the server certificate** (and, for
  `verify-full`, the hostname). The CA bundle is resolved automatically: the connection's `ssl_ca`
  → the `DBMIG_SSL_CA_FILE` env var → the bundled **`certifi`** roots. **Important:** RDS/Aurora
  *database* server certificates are issued by the RDS private CA, which is **not** in certifi — so
  for `verify-*` against RDS/Aurora you must point `ssl_ca`/`DBMIG_SSL_CA_FILE` at the
  [Amazon RDS CA bundle](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html)
  (`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`). certifi is only the fallback
  for servers with publicly-trusted certificates.
- `disable` — explicit, clearly-named opt-out (plaintext).

Use `verify-full` (with the RDS CA bundle) when you want man-in-the-middle protection; `require`
protects against passive eavesdropping with zero certificate management.

**Sources — Oracle / SQL Server.** A source database's transport security is the customer's existing
posture prior to migration, so encryption is **opt-in via the endpoint**: set **`protocol: tcps`** on
the source connection to use TLS; otherwise the connector uses plain TCP.

- **Oracle** (`oracledb`, thin): `protocol: tcps` opens a TLS session. By default it is encrypt-only
  (no certificate management); set `sslmode: verify-ca`/`verify-full` to also verify the server
  certificate/DN (CA via `ssl_ca`/`DBMIG_SSL_CA_FILE`/certifi).
- **SQL Server** (`python-tds`): `protocol: tcps` encrypts the full session. The driver requires a CA
  file to encrypt (defaulted to certifi) and **`pyOpenSSL`** (declared in requirements); with
  `sslmode: verify-full` it also validates the certificate hostname. Without `protocol: tcps` the
  session is unencrypted.

**Bottom line:** targets are encrypted by default (`require`), sources encrypt when the endpoint is
`tcps`, and `disable` / plain `tcp` are explicit opt-outs. For full server authentication use
`verify-full` (or `verify-ca`) with the RDS CA bundle (or a CA you supply via
`ssl_ca`/`DBMIG_SSL_CA_FILE`).

## SQL construction

A migration tool must name schemas, tables, and columns directly in SQL (identifiers cannot be
passed as query parameters). To keep that safe:

- identifiers are validated against a strict allowlist (`assert_identifier`) and/or quoted by the
  engine before interpolation;
- all **data values** are passed as bound driver parameters, never string-formatted;
- SQL text is assembled in dedicated **builder functions** (e.g. `build_row_count_sql`,
  `build_copy_sql`) that return a finished string; callers pass that string to the driver's
  `execute()`. This keeps the (validated) identifier interpolation out of the `execute()` call site.

Static analyzers (bandit `B608`, semgrep raw-query) flag identifier interpolation as a possible
injection vector. The builder f-strings that concatenate identifiers carry `# nosec B608`; they are
reviewed and accepted as mitigated by the controls above, because identifiers originate from the
operator's own connection config and source-catalog metadata, not from untrusted input. New
SQL-building code must keep building via a helper that uses `assert_identifier`/quoting for
identifiers and bound parameters for values.

## Reporting

Open an issue to report a security concern — please omit any real credentials or customer data.
