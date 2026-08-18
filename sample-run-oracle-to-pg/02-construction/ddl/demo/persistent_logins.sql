-- Converted from Oracle DEMO.PERSISTENT_LOGINS -> PostgreSQL demo.persistent_logins
-- Decisions:
--   This is the schema's ONE Index-Organized Table (IOT). PostgreSQL has no IOT —
--   convert to an ordinary heap table with a PRIMARY KEY. The PK's B-tree provides the
--   lookup path; physical row clustering is not preserved (optionally `CLUSTER` later).
--   Ref: tables-indexes/index-organized-and-cluster-tables.md
--   VARCHAR2(64) is BYTE-semantic here (no CHAR qualifier); under UTF-8 varchar(64) counts
--   CHARACTERS, so it is >= the source capacity — safe for the copy.
--   SERIES is the PK; PostgreSQL implies NOT NULL (Oracle did too, via the PK).
--   No IDENTITY, no foreign keys in the source.

CREATE TABLE demo.persistent_logins (
    username   varchar(64) NOT NULL,
    series     varchar(64) NOT NULL,
    token      varchar(64) NOT NULL,
    last_used  timestamp(6) NOT NULL,
    CONSTRAINT pk_persistent_logins PRIMARY KEY (series)
);
