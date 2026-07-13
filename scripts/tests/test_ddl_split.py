from dbmig.conversion.ddl_split import (
    split_statements, is_post_data, partition_ddl)

BOOKS = """-- DEMO.BOOKS -> demo.books
CREATE TABLE demo.books (
    id bigint PRIMARY KEY,
    title varchar(255),
    search_text varchar(1000)
);

CREATE INDEX idx_books_isbn ON demo.books (isbn);

ALTER TABLE demo.books ADD CONSTRAINT fk_books_genre
    FOREIGN KEY (genre_id) REFERENCES demo.genres (id);

-- Trigger: maintain search_text
CREATE OR REPLACE FUNCTION demo.trg_book_search_text() RETURNS trigger AS $$
BEGIN
    NEW.search_text := lower(NEW.title) || ';' || lower(coalesce(NEW.isbn, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_book_search_text
    BEFORE INSERT OR UPDATE OF title ON demo.books
    FOR EACH ROW EXECUTE FUNCTION demo.trg_book_search_text();
"""


def test_split_respects_dollar_quoted_body():
    stmts = split_statements(BOOKS)
    # The function body contains a ';' inside $$ ... $$ that must NOT split it.
    fn = [s for s in stmts if "RETURNS trigger" in s]
    assert len(fn) == 1
    assert "RETURN NEW;" in fn[0]
    # CREATE TABLE, CREATE INDEX, ALTER FK, CREATE FUNCTION, CREATE TRIGGER = 5
    assert len(stmts) == 5


def test_classify_fk_and_trigger_as_post_data():
    assert is_post_data("ALTER TABLE demo.books ADD CONSTRAINT fk FOREIGN KEY (g) "
                        "REFERENCES demo.genres (id)")
    assert is_post_data("CREATE TRIGGER t BEFORE INSERT ON demo.books "
                        "FOR EACH ROW EXECUTE FUNCTION f()")
    # the trigger FUNCTION itself is pre-data (only the binding is deferred)
    assert not is_post_data("CREATE OR REPLACE FUNCTION f() RETURNS trigger AS $$ "
                            "BEGIN RETURN NEW; END; $$ LANGUAGE plpgsql")
    assert not is_post_data("CREATE TABLE demo.books (id bigint PRIMARY KEY)")
    assert not is_post_data("CREATE INDEX i ON demo.books (isbn)")
    # a CHECK/UNIQUE ALTER is pre-data (enforced during load), only FK defers
    assert not is_post_data("ALTER TABLE demo.books ADD CONSTRAINT c CHECK (year > 0)")


def test_partition_separates_fk_and_trigger():
    pre, post = partition_ddl(BOOKS)
    assert "CREATE TABLE" in pre and "CREATE INDEX" in pre
    assert "RETURNS trigger" in pre               # function stays pre-data
    assert "FOREIGN KEY" not in pre
    assert "CREATE TRIGGER" not in pre
    assert "FOREIGN KEY" in post
    assert "CREATE TRIGGER trg_book_search_text" in post


def test_partition_empty_post_when_no_fk_or_trigger():
    pre, post = partition_ddl("CREATE TABLE t (id int PRIMARY KEY);\n"
                              "CREATE INDEX i ON t (id);")
    assert post == ""
    assert "CREATE TABLE" in pre


def test_order_items_three_fks_all_post():
    ddl = """CREATE TABLE demo.order_items (id bigint PRIMARY KEY, order_id bigint);
ALTER TABLE demo.order_items ADD CONSTRAINT fk1 FOREIGN KEY (order_id) REFERENCES demo.orders (id);
ALTER TABLE demo.order_items ADD CONSTRAINT fk2 FOREIGN KEY (book_id) REFERENCES demo.books (id);
ALTER TABLE demo.order_items ADD CONSTRAINT fk3 FOREIGN KEY (listing_id) REFERENCES demo.listings (id);"""
    pre, post = partition_ddl(ddl)
    assert pre.count("FOREIGN KEY") == 0
    assert post.count("FOREIGN KEY") == 3


# ---- M5: robust FK detection + inline-FK extraction ----------------------

def test_add_column_containing_foreign_key_text_is_not_post_data():
    # An ALTER ... ADD COLUMN whose text merely mentions FOREIGN KEY (in a name,
    # default literal, or comment) must NOT be misclassified as an FK deferral.
    assert not is_post_data(
        "ALTER TABLE t ADD COLUMN note varchar DEFAULT 'contains FOREIGN KEY'")
    assert not is_post_data("ALTER TABLE t ADD COLUMN foreign_key_ref integer")
    assert not is_post_data(
        "ALTER TABLE t ADD /* the FOREIGN KEY comes later */ COLUMN c int")


def test_add_named_and_unnamed_fk_is_post_data():
    assert is_post_data("ALTER TABLE t ADD FOREIGN KEY (p) REFERENCES parent (id)")
    assert is_post_data(
        'ALTER TABLE t ADD CONSTRAINT "fk_x" FOREIGN KEY (p) REFERENCES parent (id)')


def test_inline_table_level_fk_extracted_to_post():
    ddl = (
        "CREATE TABLE demo.orders (\n"
        "  id bigint PRIMARY KEY,\n"
        "  cust_id bigint,\n"
        "  amount numeric(10,2),\n"
        "  CONSTRAINT fk_cust FOREIGN KEY (cust_id) REFERENCES demo.customers (id)\n"
        ");")
    pre, post = partition_ddl(ddl)
    # The FK clause is pulled out of CREATE TABLE so it never forces load ordering.
    assert "FOREIGN KEY" not in pre
    assert "CREATE TABLE demo.orders" in pre
    assert "numeric(10,2)" in pre           # nested-paren comma preserved
    assert "cust_id bigint" in pre
    assert "ALTER TABLE demo.orders ADD CONSTRAINT fk_cust FOREIGN KEY" in post
    assert "REFERENCES demo.customers (id)" in post


def test_inline_unnamed_fk_extracted_to_post():
    ddl = ("CREATE TABLE t (\n"
           "  id int PRIMARY KEY,\n"
           "  p int,\n"
           "  FOREIGN KEY (p) REFERENCES parent (id)\n"
           ");")
    pre, post = partition_ddl(ddl)
    assert "FOREIGN KEY" not in pre
    assert "ALTER TABLE t ADD FOREIGN KEY (p) REFERENCES parent (id)" in post


def test_create_table_without_inline_fk_unchanged():
    ddl = "CREATE TABLE t (id int PRIMARY KEY, amount numeric(10,2), UNIQUE (id));"
    pre, post = partition_ddl(ddl)
    assert post == ""
    assert "CREATE TABLE t" in pre and "numeric(10,2)" in pre and "UNIQUE (id)" in pre
