-- Converted from Oracle DEMO.BOOKS_COVER -> PostgreSQL demo.books_cover
-- Decisions:
--   BLOB COVER_IMAGE   -> bytea (datatype-map.yaml Binary; ~1GB practical limit, cover images are far below)
--   SYS_C* unique idx  -> dropped (PK provides it)
--   SYS_IL0000...$$    -> dropped: internal Oracle LOB index; PostgreSQL TOAST manages bytea storage
--                         (non-portable-constructs.md → Indexes / LOB indexes)
--   No IDENTITY here: BOOK_ID is a natural PK shared with BOOKS (1:1 cover row)

CREATE TABLE demo.books_cover (
    book_id       bigint NOT NULL,
    cover_image   bytea,
    content_type  varchar(100),
    file_name     varchar(255),
    created_on    timestamp(6),
    updated_on    timestamp(6),
    CONSTRAINT pk_books_cover PRIMARY KEY (book_id)
);

-- deferred (post-data)
ALTER TABLE demo.books_cover
    ADD CONSTRAINT fk_books_cover_book FOREIGN KEY (book_id)
    REFERENCES demo.books (id) ON DELETE CASCADE;
