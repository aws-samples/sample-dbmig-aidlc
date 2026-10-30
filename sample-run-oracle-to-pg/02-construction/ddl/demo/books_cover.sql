-- DEMO.BOOKS_COVER -> demo.books_cover; BLOB -> bytea. SYS_IL... LOB index is internal (dropped).
CREATE TABLE demo.books_cover (
    book_id      bigint NOT NULL,
    cover_image  bytea,
    content_type varchar(100),
    file_name    varchar(255),
    created_on   timestamp(6),
    updated_on   timestamp(6),
    CONSTRAINT books_cover_pkey PRIMARY KEY (book_id)
);
ALTER TABLE demo.books_cover ADD CONSTRAINT fk_books_cover_book
    FOREIGN KEY (book_id) REFERENCES demo.books (id) ON DELETE CASCADE;
