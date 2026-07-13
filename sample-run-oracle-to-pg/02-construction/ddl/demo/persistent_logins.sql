-- DEMO.PERSISTENT_LOGINS -> demo.persistent_logins
-- Spring Security remember-me table: primary key is SERIES (no surrogate identity).
CREATE TABLE demo.persistent_logins (
    username  varchar(64) NOT NULL,
    series    varchar(64) NOT NULL,
    token     varchar(64) NOT NULL,
    last_used timestamp(6) NOT NULL,
    CONSTRAINT persistent_logins_pk PRIMARY KEY (series)
);
