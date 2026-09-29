CREATE TABLE demo.books_cover (
  book_id bigint PRIMARY KEY,
  cover_image bytea,                   -- BLOB; SYS_IL LOB index dropped (TOAST)
  content_type varchar(100), file_name varchar(255),
  created_on timestamp(6), updated_on timestamp(6)
);
ALTER TABLE demo.books_cover ADD CONSTRAINT fk_books_cover_book FOREIGN KEY (book_id) REFERENCES demo.books (id) ON DELETE CASCADE;
