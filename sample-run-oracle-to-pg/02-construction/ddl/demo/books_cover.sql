-- DEMO.BOOKS_COVER -> demo.books_cover
-- BLOB -> bytea (PG TOAST handles large-value storage; the Oracle internal LOB index is not needed).
-- FK to books (ON DELETE CASCADE) deferred to post-data.
CREATE TABLE demo.books_cover (
    book_id      bigint NOT NULL,
    cover_image  bytea,
    content_type varchar(100),
    file_name    varchar(255),
    created_on   timestamp(6),
    updated_on   timestamp(6),
    CONSTRAINT books_cover_pk PRIMARY KEY (book_id)
);

ALTER TABLE demo.books_cover ADD CONSTRAINT fk_books_cover_book
    FOREIGN KEY (book_id) REFERENCES demo.books (id) ON DELETE CASCADE;
