"""app-scan coverage across the stacks named by the app-modernization skills:
JPA/Hibernate, EF Core (annotations + fluent + base classes), MyBatis XML, Dapper /
ADO.NET, SQLAlchemy (classic + 2.0), Django, TypeORM, Sequelize, Prisma, raw
drivers — plus literal reconstruction per language and ORM type obligations."""
import textwrap

from dbmig import appscan as A
from dbmig.commands import app_scan


def _w(root, rel, body):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body))


# ---- literal reconstruction ------------------------------------------------

def test_literals_java_concat_and_text_block():
    src = 'q = "SELECT * FROM t " +\n    "WHERE ROWNUM < 5";\n// "SELECT in comment"\nString s = """\n  SELECT NVL(a,0)\n  FROM dual""";\n'
    lits = A.string_literals(src, "java")
    assert (1, "SELECT * FROM t WHERE ROWNUM < 5") in lits
    assert any(ln == 4 and "NVL(a,0)" in b for ln, b in lits)
    assert not any("in comment" in b for _, b in lits)


def test_literals_csharp_verbatim_interpolated():
    src = 'var a = @"SELECT TOP 5 *\n  FROM [dbo].[Book]";\nvar b = $"SELECT ISNULL(x,0) FROM t WHERE id={id}";\nchar c = \'"\';\n'
    lits = [b for _, b in A.string_literals(src, "cs")]
    assert any("TOP 5" in b and "[dbo].[Book]" in b for b in lits)
    assert any("ISNULL" in b for b in lits)


def test_literals_python_and_js():
    py = 'q = ("SELECT SYSDATE "\n     "FROM dual")\nr = """UPDATE t\nSET a = NVL(b, 0)"""\n# "SELECT nope"\n'
    lits = [b for _, b in A.string_literals(py, "py")]
    assert "SELECT SYSDATE FROM dual" in lits and any("NVL(b, 0)" in b for b in lits)
    assert not any("nope" in b for b in lits)
    js = "const q = `SELECT TOP 10 *\n FROM users`;\nconst r = 'SELECT GETDATE()';\n"
    lits = [b for _, b in A.string_literals(js, "js")]
    assert any("TOP 10" in b for b in lits) and "SELECT GETDATE()" in lits


# ---- mapping extractors ----------------------------------------------------

def test_jpa_entity():
    src = """
    @Entity
    @Table(name = "books", schema = "demo")
    public class Book {
        @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
        @Column(name = "is_featured", columnDefinition = "NUMBER(1)") private Boolean featured;
        private LocalDate publishDate;
        @Lob private byte[] cover;
        @ManyToOne @JoinColumn(name = "genre_id") private Genre genre;
        @OneToMany(mappedBy = "book") private List<Listing> listings;
        @Transient private String tmp;
        private static final int X = 1;
    }"""
    [e] = A.extract_jpa(textwrap.dedent(src), "Book.java")
    f = {x["field"]: x for x in e["fields"]}
    assert e["table"] == "books" and e["schema"] == "demo"
    assert set(f) == {"id", "featured", "publishDate", "cover", "genre"}
    assert f["featured"]["column"] == "is_featured" and f["featured"]["column_definition"] == "NUMBER(1)"
    assert f["publishDate"]["column"] == "publish_date" and f["cover"]["lob"]
    assert f["genre"]["relation"] and f["genre"]["column"] == "genre_id"


def test_ef_core_annotations_fluent_and_base_class(tmp_path):
    _w(tmp_path, "Domain/Entity.cs", """
        public abstract class Entity { public int Id { get; set; } public DateTime CreatedOn { get; set; } }""")
    _w(tmp_path, "Domain/Book.cs", """
        [Table("book", Schema = "store")]
        public class Book : Entity {
            [Column("name")] public string Name { get; set; }
            public bool IsActive { get; set; }
            public ReferenceDataItem Genre { get; set; }
            public int GenreId { get; set; }
            public ICollection<OrderItem> Items { get; set; }
            [NotMapped] public bool IsInStock => true;
        }
        public class ReferenceDataItem : Entity { public string Text { get; set; } }""")
    _w(tmp_path, "Data/Ctx.cs", """
        public class Ctx : DbContext {
            public DbSet<Book> Book { get; set; }
            public DbSet<Order> Orders { get; set; }
            protected override void OnModelCreating(ModelBuilder modelBuilder) {
                modelBuilder.Entity<Order>().ToTable("Orders");
                modelBuilder.Entity<Book>(entity => {
                    entity.Property(e => e.IsActive).HasColumnName("isactive").HasColumnType("bit");
                });
            }
        }
        public class Order : Entity { public decimal Total { get; set; } }""")
    r = app_scan.scan(tmp_path, "sqlserver-to-postgresql", None, check_target=False)
    ents = {e["class"]: e for e in r["entities"]}
    assert "EF Core" in r["frameworks"]
    assert ents["Book"]["table"] == "book" and ents["Book"]["schema"] == "store"
    assert ents["Order"]["table"] == "Orders"
    rows = {(x["entity"], x["field"]): x for x in r["type_crosscheck"]["rows"]}
    assert rows[("Book", "Name")]["column"] == "name"
    assert rows[("Book", "IsActive")]["column"] == "isactive"
    assert ("Book", "Id") in rows and ("Book", "CreatedOn") in rows      # inherited
    assert ("Book", "Genre") not in rows and ("Book", "Items") not in rows  # navigations
    assert ("Book", "IsInStock") not in rows


def test_python_sqlalchemy_and_django():
    sa = """
class Base(DeclarativeBase): pass
class Book(Base):
    __tablename__ = "books"
    __table_args__ = {"schema": "demo"}
    id = Column(Integer, primary_key=True)
    featured = Column("is_featured", Boolean)
    published: Mapped[date] = mapped_column(Date)
"""
    [e] = A.extract_python(sa, "models.py")
    f = {x["field"]: x for x in e["fields"]}
    assert e["orm"] == "SQLAlchemy" and e["table"] == "books" and e["schema"] == "demo"
    assert f["featured"]["column"] == "is_featured" and f["featured"]["java_type"] == "Boolean"
    dj = """
class Book(models.Model):
    title = models.CharField(max_length=100)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    active = models.BooleanField(db_column="is_active")
    class Meta:
        db_table = "books"
"""
    [e] = A.extract_python(dj, "shop/models.py")
    f = {x["field"]: x for x in e["fields"]}
    assert e["orm"] == "Django ORM" and e["table"] == "books"
    assert f["genre"]["column"] == "genre_id" and f["active"]["column"] == "is_active"


def test_typeorm_sequelize_prisma():
    ts = """
@Entity("books")
export class Book {
  @PrimaryGeneratedColumn() id: number;
  @Column({ name: "is_featured", type: "smallint" }) featured: boolean;
}"""
    [e] = A.extract_js(ts, "book.ts")
    assert e["orm"] == "TypeORM" and e["table"] == "books"
    assert e["fields"][1]["column"] == "is_featured" and e["fields"][1]["column_type"] == "smallint"
    sq = """const Book = sequelize.define('Book', {
  title: { type: DataTypes.STRING, field: 'book_title' },
  featured: DataTypes.BOOLEAN
}, { tableName: 'books' });"""
    [e] = A.extract_js(sq, "book.js")
    f = {x["field"]: x for x in e["fields"]}
    assert e["orm"] == "Sequelize" and e["table"] == "books" and f["title"]["column"] == "book_title"
    pr = """model Book {
  id       Int     @id
  featured Boolean @map("is_featured") @db.SmallInt
  genre    Genre   @relation(fields: [genreId], references: [id])
  @@map("books")
}"""
    [e] = A.extract_prisma(pr, "schema.prisma")
    assert e["table"] == "books" and [x["field"] for x in e["fields"]] == ["id", "featured"]


# ---- whole-tree scan: SQL sites, routines, mybatis, dapper, vendored, leftovers --

def test_scan_tree_sites(tmp_path):
    _w(tmp_path, "src/Repo.java", '''
        public interface Repo {
          @Query(value = "SELECT b.* FROM books b " +
                         "WHERE CONTAINS(b.t, ?1, 1) > 0 ORDER BY SCORE(1) DESC", nativeQuery = true)
          List<Book> search(String q);
          @Query(value = "{ call get_history(:id) }", nativeQuery = true) void hist(Long id);
          // Execute the job later (comment, not a routine)
        }''')
    _w(tmp_path, "src/Dyn.java", '''
        class Dyn { String q() { StringBuilder sql = new StringBuilder("SELECT * FROM books WHERE 1=1 ");
          sql.append("AND created > TO_DATE('2023-01-01', 'YYYY-MM-DD') "); String msg = "TRUNC is fine";
          return sql.toString(); } }''')
    _w(tmp_path, "src/Svc.java", 'class S { String q(String t) { return "fuzzy(" + t + ", 40)"; } }')
    _w(tmp_path, "src/Plain.java", 'class P { String m = "call TRUNC later"; }')
    _w(tmp_path, "src/main/resources/mapper/BookMapper.xml",
       '<mapper namespace="x"><select id="a">SELECT NVL(a,0) FROM dual</select></mapper>')
    _w(tmp_path, "src/main/resources/application.properties",
       "spring.datasource.url=jdbc:oracle:thin:@//h:1521/ORCL\nspring.datasource.password=hunter2\n")
    _w(tmp_path, "src/main/resources/db/schema.sql", "CREATE TABLE t (a NUMBER DEFAULT SYSDATE);")
    _w(tmp_path, "src/main/resources/static/lib/jquery.js", "var q='SELECT SUBSTR x';")
    _w(tmp_path, "src/Old.java.bak", "x")
    _w(tmp_path, "target/classes/Stale.java", 'String q = "SELECT SYSDATE FROM dual";')
    r = app_scan.scan(tmp_path, "oracle-to-postgresql", None, check_target=False)
    s = r["sites"]
    dial = {(x["file"], tuple(x["constructs"])) for x in s["sql"] if x["constructs"]}
    assert ("src/Repo.java", ("CONTAINS(", "SCORE(")) in dial
    assert any(f.endswith("BookMapper.xml") for f, _ in dial)            # MyBatis
    frag = [x for x in s["sql"] if x.get("fragment")]
    assert [(x["file"], x["constructs"]) for x in frag if "TO_DATE" in x["constructs"]] == [("src/Dyn.java", ["TO_DATE"])]
    assert not any(x["file"] == "src/Plain.java" for x in s["sql"])     # no SQL in file
    assert any(x["file"] == "src/Svc.java" and "full-text query syntax" in x["constructs"][0]
               for x in s["sql"])                                      # Oracle Text query builder
    assert [x["file"] for x in s["routine"]] == ["src/Repo.java"]      # comment ignored
    assert any(x.get("kind") == "plaintext-secret" and "hunter2" not in x["text"] for x in s["config"])
    assert not A.SECRET_RE.search('"SaveToken": true,') and not A.SECRET_RE.search("password=${DB_PASSWORD}")
    assert A.SECRET_RE.search('"Password": "p4ss"') and A.SECRET_RE.search("db.password=x")
    assert [x["file"] for x in s["db_scripts"]] == ["src/main/resources/db/schema.sql"]
    assert r["leftovers"] == ["src/Old.java.bak"]
    assert not any("jquery" in x["file"] or "Stale" in x["file"] for x in s["sql"])


def test_scan_dotnet_dapper_adonet(tmp_path):
    _w(tmp_path, "Repo.cs", '''
        using Dapper;
        public class R {
          public void A(SqlConnection c) {
            c.Query<Book>(@"SELECT TOP 10 * FROM [dbo].[Book]
                            WHERE Created > DATEADD(day, -1, GETDATE())");
            var cmd = new SqlCommand("usp_GetBooks", c) { CommandType = CommandType.StoredProcedure };
            var n = reader.GetInt32(0);
          }
        }''')
    r = app_scan.scan(tmp_path, "sqlserver-to-postgresql", None, check_target=False)
    assert {"Dapper", "ADO.NET"} <= set(r["frameworks"])
    [site] = [x for x in r["sites"]["sql"] if x["constructs"]]
    assert {"TOP ", "[dbo]", "DATEADD", "GETDATE"} <= set(site["constructs"])
    assert r["sites"]["routine"] and r["sites"]["resultset"]


# ---- obligations ------------------------------------------------------------

def test_obligations_per_orm():
    ob = A.obligation
    jb = {"java_type": "Boolean"}
    assert "SMALLINT" in ob(jb, "smallint", "JPA/Hibernate")
    assert "HasConversion<short>" in ob({"java_type": "bool"}, "smallint", "EF Core")
    assert ob({"java_type": "Boolean", "jdbc_type_code": "SMALLINT"}, "smallint", "JPA/Hibernate") is None
    assert ob({"java_type": "bool"}, "boolean", "EF Core") is None
    assert "HasConversion(v => v != 0" in ob({"java_type": "int"}, "boolean", "EF Core")
    assert "TIMESTAMP" in ob({"java_type": "LocalDate"}, "timestamp without time zone", "JPA/Hibernate")
    assert "VARBINARY" in ob({"java_type": "byte[]", "lob": True}, "bytea", "JPA/Hibernate")
    assert "long" in ob({"java_type": "int"}, "bigint", "EF Core")
    assert A.is_advisory(ob({"java_type": "Integer"}, "bigint", "JPA/Hibernate"))
    assert not A.is_advisory(ob({"java_type": "int"}, "bigint", "EF Core"))
    assert "date-only" in ob({"java_type": "DateTime"}, "date", "EF Core")
    assert "Utc" in ob({"java_type": "DateTime"}, "timestamp with time zone", "EF Core")
    assert "source-engine column type" in ob(
        {"java_type": "string", "column_type": "nvarchar(max)"}, "text", "EF Core")
    assert ob({"java_type": "Genre", "relation": True}, "bigint", "JPA/Hibernate") is None


def test_ef_identifier_case_issue(tmp_path, monkeypatch):
    _w(tmp_path, "Ctx.cs", """
        public class Ctx : DbContext { public DbSet<Book> Book { get; set; } }
        public class Book { public int Id { get; set; } public string Name { get; set; } }""")
    monkeypatch.setattr(app_scan, "_target_columns",
                        lambda s: ({("book", "id"): "integer", ("book", "name"): "text"}, None, "s"))
    r = app_scan.scan(tmp_path, "sqlserver-to-postgresql", None)
    issues = [x["issue"] for x in r["type_crosscheck"]["rows"] if x.get("issue")]
    assert issues and all("identifier case" in i for i in issues)
    md = app_scan.render_md(r)
    assert "C1. Mapping issues" in md and "fold names in the model" in md
