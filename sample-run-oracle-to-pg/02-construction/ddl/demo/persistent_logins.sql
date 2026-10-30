-- DEMO.PERSISTENT_LOGINS -> demo.persistent_logins (Spring Security remember-me table)
CREATE TABLE demo.persistent_logins (
    username  varchar(64) NOT NULL,
    series    varchar(64) NOT NULL,
    token     varchar(64) NOT NULL,
    last_used timestamp(6) NOT NULL,
    CONSTRAINT persistent_logins_pkey PRIMARY KEY (series)
);
