"""Connection modeling and engine connectors (oracledb thin + psycopg3)."""
from __future__ import annotations

import os
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import config

# Connection establishment timeout (seconds); override with DBMIG_CONNECT_TIMEOUT.
try:
    CONNECT_TIMEOUT = int(os.environ.get("DBMIG_CONNECT_TIMEOUT", "30"))
except ValueError:
    CONNECT_TIMEOUT = 30


@dataclass
class Connection:
    engine: str
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    service_name: Optional[str] = None
    sid: Optional[str] = None
    database: Optional[str] = None
    # Secure by default: 'require' insists on an encrypted channel (no plaintext
    # fallback). Used by the target connectors (PostgreSQL / MySQL). See db_connect.
    sslmode: str = "require"
    # Source (Oracle / SQL Server) transport: 'tcp' (default) or 'tcps' (TLS).
    protocol: Optional[str] = None
    default_schema: Optional[str] = None
    version: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Connection":
        if not d:
            raise config.ConfigError("empty connection block")
        engine = (d.get("engine") or "").strip().lower()
        if not engine:
            raise config.ConfigError("connection is missing 'engine'")
        port = d.get("port") or 0
        try:
            port = int(port) if port else 0
        except (TypeError, ValueError):
            raise config.ConfigError(f"invalid port: {port!r}")
        known = {
            "engine", "host", "port", "username", "password", "service_name",
            "sid", "database", "sslmode", "protocol", "default_schema", "version",
        }
        return cls(
            engine=engine,
            host=str(d.get("host") or ""),
            port=port,
            username=str(d.get("username") or ""),
            password=str(d.get("password") or ""),
            service_name=(d.get("service_name") or None),
            sid=(d.get("sid") or None),
            database=(d.get("database") or None),
            sslmode=str(d.get("sslmode") or "require"),
            protocol=(str(d["protocol"]).strip().lower() if d.get("protocol") else None),
            default_schema=(d.get("default_schema") or None),
            version=(str(d["version"]) if d.get("version") is not None else None),
            extra={k: v for k, v in d.items() if k not in known},
        )

    # ---- safe display -----------------------------------------------------
    def safe(self) -> str:
        loc = self.service_name or self.sid or self.database or ""
        return f"{self.engine}://{self.username}@{self.host}:{self.port}/{loc}"

    def __repr__(self) -> str:  # never leak the password
        return f"Connection({self.safe()})"


def load_pair() -> Dict[str, Connection]:
    raw = config.load_connections()
    out: Dict[str, Connection] = {}
    for side in ("source", "target"):
        if side in raw and raw[side]:
            out[side] = Connection.from_dict(raw[side])
    if "source" not in out and "target" not in out:
        raise config.ConfigError(
            "connections file must define 'source' and/or 'target' blocks")
    return out


# ---- connectors -----------------------------------------------------------

def _resolve_ca_file(c: "Connection") -> Optional[str]:
    """CA bundle used to *verify* a server certificate (verify-ca / verify-full,
    and SQL Server tcps). Precedence: the connection's ``ssl_ca`` → the
    ``DBMIG_SSL_CA_FILE`` env var → the ``certifi`` bundle.

    NOTE: Amazon RDS/Aurora *database* server certificates are issued by the RDS
    private CA hierarchy, which is **not** in the certifi/Mozilla store. To use
    verify-ca/verify-full against RDS/Aurora, point ``ssl_ca`` / ``DBMIG_SSL_CA_FILE``
    at the RDS CA bundle (https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem).
    certifi is only the fallback for servers with publicly-trusted certificates."""
    ca = c.extra.get("ssl_ca") or os.environ.get("DBMIG_SSL_CA_FILE")
    if ca:
        return str(ca)
    try:
        import certifi
        return certifi.where()
    except Exception:
        return None


def _connect_oracle(c: Connection):
    import oracledb  # imported lazily so the package imports without the driver

    # Return CLOB/metadata as str rather than LOB locators (simpler DDL handling).
    try:
        oracledb.defaults.fetch_lobs = False
    except Exception:
        pass

    if not (c.service_name or c.sid):
        raise config.ConfigError("Oracle connection needs service_name or sid")

    kw: Dict[str, Any] = dict(
        user=c.username, password=c.password,
        host=c.host, port=c.port or 1521,
        tcp_connect_timeout=CONNECT_TIMEOUT,
    )
    if c.service_name:
        kw["service_name"] = c.service_name
    else:
        kw["sid"] = c.sid

    # Source database: encrypt the session only when the endpoint is TLS
    # (protocol: tcps). Otherwise connect over plain TCP — a source DB's transport
    # security is the customer's existing posture prior to migration.
    proto = (c.protocol or c.extra.get("protocol") or "tcp").strip().lower()
    if proto == "tcps":
        mode = (c.sslmode or "").strip().lower()
        kw["protocol"] = "tcps"
        if mode in ("verify-ca", "verify-full"):
            ca = _resolve_ca_file(c)
            kw["ssl_context"] = (ssl.create_default_context(cafile=ca)
                                 if ca else ssl.create_default_context())
            kw["ssl_server_dn_match"] = (mode == "verify-full")
        else:
            # Encrypt-only (no certificate verification) — no CA to manage.
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kw["ssl_context"] = ctx
            kw["ssl_server_dn_match"] = False
    # Thin mode is the default (no Oracle Client libraries required).
    return oracledb.connect(**kw)


def _connect_postgres(c: Connection):
    import psycopg  # imported lazily

    if not c.database:
        raise config.ConfigError("PostgreSQL connection needs 'database'")
    # Target = Aurora/RDS PostgreSQL (TLS enabled by default). 'require' (the
    # default) insists on an encrypted channel with no plaintext fallback;
    # 'verify-ca'/'verify-full' additionally authenticate the server certificate
    # (CA via certifi by default). 'disable' is an explicit opt-out.
    mode = (c.sslmode or "require").strip().lower()
    params: Dict[str, Any] = dict(
        host=c.host,
        port=c.port or 5432,
        user=c.username,
        password=c.password,
        dbname=c.database,
        sslmode=mode,
        connect_timeout=CONNECT_TIMEOUT,
    )
    if mode in ("verify-ca", "verify-full"):
        ca = _resolve_ca_file(c)
        if ca:
            params["sslrootcert"] = ca
    conninfo = psycopg.conninfo.make_conninfo(**params)
    return psycopg.connect(conninfo)


def _connect_mysql(c: Connection):
    import pymysql  # imported lazily (pure-Python driver — no native client)
    from pymysql.constants import CLIENT

    kwargs = dict(
        host=c.host,
        port=c.port or 3306,
        user=c.username,
        password=c.password,
        autocommit=False,
        charset="utf8mb4",
        connect_timeout=CONNECT_TIMEOUT,
        # A converted object-unit can carry several statements (e.g. a table's
        # deferred ALTER ... ADD FOREIGN KEY constraints, or CREATE TRIGGER + ...).
        # Unlike psycopg, pymysql rejects multiple statements in one execute() unless
        # MULTI_STATEMENTS is enabled. The server still parses a compound CREATE
        # FUNCTION/PROCEDURE/TRIGGER (BEGIN ... END) as a single statement, so this is
        # safe for both cases. apply_sql() drains the extra result sets.
        client_flag=CLIENT.MULTI_STATEMENTS,
    )
    if c.database:
        kwargs["database"] = c.database
    # Target = Aurora/RDS MySQL (TLS enabled by default). 'require' (the default)
    # opens an encrypted connection with no plaintext fallback. Note: an empty
    # ssl={} is falsy in pymysql and would silently *disable* TLS, so we pass an
    # explicit no-verify SSLContext to force encryption. 'verify-ca'/'verify-full'
    # also authenticate the server certificate (CA via certifi by default).
    # 'disable' is an explicit opt-out.
    mode = (c.sslmode or "require").strip().lower()
    if mode == "disable":
        pass
    elif mode in ("verify-ca", "verify-full"):
        ca = _resolve_ca_file(c)
        if ca:
            kwargs["ssl_ca"] = ca
        kwargs["ssl_verify_cert"] = True
        kwargs["ssl_verify_identity"] = (mode == "verify-full")
    else:  # require (default), prefer, allow → encrypt without verification
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl"] = ctx
    return pymysql.connect(**kwargs)


def _connect_sqlserver(c: Connection):
    import pytds  # imported lazily (python-tds; pure-Python SQL Server driver)

    kwargs = dict(
        server=c.host,
        port=c.port or 1433,
        user=c.username,
        password=c.password,
        autocommit=False,
        login_timeout=CONNECT_TIMEOUT,
    )
    if c.database:
        kwargs["database"] = c.database
    # Source database: encrypt the session only when the endpoint is TLS
    # (protocol: tcps). python-tds encrypts the full session only when given a CA
    # file (and needs pyOpenSSL); the CA defaults to certifi. Otherwise connect in
    # the clear — a source DB's transport security is the customer's existing
    # posture prior to migration.
    proto = (c.protocol or c.extra.get("protocol") or "tcp").strip().lower()
    if proto == "tcps":
        ca = _resolve_ca_file(c)
        if not ca:
            raise config.ConfigError(
                "SQL Server 'protocol: tcps' needs a CA bundle to encrypt: install "
                "certifi (bundled) or set DBMIG_SSL_CA_FILE / ssl_ca. TLS also "
                "requires pyOpenSSL.")
        kwargs["cafile"] = ca
        mode = (c.sslmode or "").strip().lower()
        # Verify the certificate hostname only for verify-full.
        kwargs["validate_host"] = (mode == "verify-full")
    return pytds.connect(**kwargs)


def db_connect(c: Connection):
    """Open a DB-API connection for the given Connection based on its engine."""
    if c.engine == "oracle":
        return _connect_oracle(c)
    if c.engine in ("postgresql", "postgres", "aurora-postgresql"):
        return _connect_postgres(c)
    if c.engine in ("mysql", "aurora-mysql", "mariadb"):
        return _connect_mysql(c)
    if c.engine in ("sqlserver", "mssql", "sql-server", "sql_server"):
        return _connect_sqlserver(c)
    raise config.ConfigError(f"unsupported engine: {c.engine}")
