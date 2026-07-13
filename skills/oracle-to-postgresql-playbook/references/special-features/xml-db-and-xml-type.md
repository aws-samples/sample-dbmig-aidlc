# XML DB and XML Type

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.xmldb.html

**Conversion category:** Assisted (Three-star feature compatibility, three-star automation)
**SCT automation:** N/A. Key difference: different paradigm and syntax will require application or driver rewrite.

## Oracle

Oracle XML DB provides native XML support including the `XMLType` data type and `XMLIndex`. XMLType represents an XML document accessible from SQL and supports XML Schema, XPath, XQuery, XSLT, DOM. XML can be schema-based (validated against XSD) or non-schema-based.

Common features: storage model **Binary XML**; indexing **XML search index / XMLIndex with structured component**; database language SQL with SQL/XML functions; XML languages XQuery and XSLT.

- **Binary XML** (default, post-parse persistence) — schema-aware, flexible, efficient partial updates and streaming query evaluation. Alternative: object-relational storage (better for structured XML with few changes).
- **Indexing** — XML Search Index gives full-text search (Oracle recommends Binary XML + XQuery Full Text). For predicates like `XMLExists` in `WHERE`, an XML search index is required.

Create XMLType tables/columns/views and insert:
```sql
CREATE TABLE orders OF XMLType;
CREATE DIRECTORY xmldir AS path_to_folder_containing_XML_file;
INSERT INTO orders VALUES (XMLType(BFILENAME('XMLDIR',
  'purOrder.xml'),NLS_CHARSET_ID('AL32UTF8')));

CREATE TABLE xwarehouses (warehouse_id NUMBER, warehouse_spec XMLTYPE);

CREATE VIEW warehouse_view AS
SELECT VALUE(p) AS warehouse_xml FROM xwarehouses p;

INSERT INTO xwarehouses
VALUES(100, '<?xml version="1.0"?>
<PO pono="1">
<PNAME>Po_1</PNAME>
<CUSTNAME>John</CUSTNAME>
<SHIPADDR>
<STREET>1033, Main Street</STREET>
<CITY>Sunnyvale</CITY>
<STATE>CA</STATE>
</SHIPADDR></PO>')
```

Create an XML search index (Oracle Text) and query with XQuery:
```sql
BEGIN
CTX_DDL.create_section_group('secgroup', 'PATH_SECTION_GROUP');
CTX_DDL.set_sec_grp_attr('secgroup', 'XML_ENABLE', 'T');
CTX_DDL.create_preference('pref', 'BASIC_STORAGE');
CTX_DDL.set_attribute('pref','D_TABLE_CLAUSE', 'TABLESPACE ts_name LOB(DOC) STORE AS
SECUREFILE(TABLESPACE ts_name COMPRESS MEDIUM CACHE)');
CTX_DDL.set_attribute('pref','I_TABLE_CLAUSE','TABLESPACE ts_name LOB(TOKEN_INFO)
STORE AS SECUREFILE(TABLESPACE ts_name NOCOMPRESS CACHE)');
END;
/
CREATE INDEX po_ctx_idx ON po_binxml(OBJECT_VALUE)
INDEXTYPE IS CTXSYS.CONTEXT
PARAMETERS('storage pref section group secgroup');

SELECT XMLQuery('for $i in /PurchaseOrder/LineItems/LineItem/Description where $i[.
contains text "Big" ftand "Street"] return <Title>{$i}</Title>'
PASSING OBJECT_VALUE RETURNING CONTENT)
FROM po_binxml
WHERE XMLExists('/PurchaseOrder/LineItems/LineItem/Description [. contains
text "Big" ftand "Street"]'
```

**XMLIndex with structured component** organizes fixed structured "islands" of XML into relational format:
```sql
CREATE INDEX po_xmlindex_ix ON po_binxml (OBJECT_VALUE)
INDEXTYPE IS XDB.XMLIndex PARAMETERS ('PATH TABLE path_tab');
BEGIN
DBMS_XMLINDEX.registerParameter(
'myparam',
'ADD_GROUP GROUP po_item
XMLTable po_idx_tab ''/PurchaseOrder''
COLUMNS reference VARCHAR2(30) PATH ''Reference'',
requestor VARCHAR2(30) PATH ''Requestor'',
username VARCHAR2(30) PATH ''User'',
lineitem XMLType PATH ''LineItems/LineItem'' VIRTUAL
XMLTable po_index_lineitem ''/LineItem'' PASSING lineitem
COLUMNS itemno BINARY_DOUBLE PATH ''@ItemNumber'',
description VARCHAR2(256) PATH ''Description'',
partno VARCHAR2(14) PATH ''Part/@Id'',
quantity BINARY_DOUBLE PATH ''Part/@Quantity'',
unitprice BINARY_DOUBLE PATH ''Part/@UnitPrice''');
END;
/
ALTER INDEX po_xmlindex_ix PARAMETERS('PARAM myparam');
```

**SQL/XML functions** — publishing (`XMLQuery`, `XMLTable`) and query/update (`XMLExists`, `XMLCast`):
```sql
-- XMLTable: generate virtual table from XML, nested
SELECT po.reference, li.*
FROM po_binaryxml p,
XMLTable('/PurchaseOrder' PASSING p.OBJECT_VALUE
COLUMNS
reference VARCHAR2(30) PATH 'Reference',
lineitem XMLType PATH 'LineItems/LineItem') po,
XMLTable('/LineItem' PASSING po.lineitem
COLUMNS
itemno NUMBER(38) PATH '@ItemNumber',
description VARCHAR2(256) PATH 'Description',
partno VARCHAR2(14) PATH 'Part/@Id',
quantity NUMBER(12, 2) PATH 'Part/@Quantity',
unitprice NUMBER(8, 4) PATH 'Part/@UnitPrice') li;

-- XMLExists in WHERE
SELECT OBJECT_VALUE FROM purchaseorder
  WHERE XMLExists('/PurchaseOrder[SpecialInstructions="Expedite"]'
  PASSING OBJECT_VALUE);

-- XMLCast scalar to VARCHAR2
SELECT XMLCast(XMLQuery('/PurchaseOrder/Reference'
  PASSING OBJECT_VALUE
  RETURNING CONTENT) AS VARCHAR2(100)) "REFERENCE"
  FROM purchaseorder
  WHERE XMLExists('/PurchaseOrder[SpecialInstructions="Expedite"]'
  PASSING OBJECT_VALUE);

-- update XMLType
UPDATE purchaseorder po
SET po.OBJECT_VALUE = XMLType(bfilename('XMLDIR','NEW-DAUSTIN-20021009123335811PDT.xml'),
  nls_charset_id('AL32UTF8'))
WHERE XMLExists('$p/PurchaseOrder[Reference="DAUSTIN-20021009123335811PDT"]'
  PASSING po.OBJECT_VALUE AS "p");
```

## PostgreSQL

PostgreSQL has an `xml` data type. The advantage over a plain text column: the input is checked (alerts on bad format) and type-safe XML functions exist. It can store well-formed "documents" or "content" fragments (multiple top-level elements). Use `IS DOCUMENT` to test whether a value is a full document.

Note: `xmltable()` and `xpath()` may not work with non-ASCII data when server encoding is not UTF-8.

```sql
CREATE TABLE test (a xml);

insert into test values (XMLPARSE (DOCUMENT '<?xml vesion=" 1.0"?><Series><title>Simpsons</title><chapter>...</chapter></Series>'));
insert into test values (XMLPARSE (CONTENT 'note<tag>value</tag><tag>value</tag>'));

select * from test where a IS DOCUMENT;
```

Convert XML to rows with `XMLTABLE` (PG 10+):
```sql
CREATE TABLE xmldata_sample AS SELECT
xml $$
<ROWS>
  <ROW id="1"><EMP_ID>532</EMP_ID><EMP_NAME>John</EMP_NAME></ROW>
  <ROW id="5"><EMP_ID>234</EMP_ID><EMP_NAME>Carl</EMP_NAME><EMP_DEP>6</EMP_DEP><SALARY unit="dollars">10000</SALARY></ROW>
  <ROW id="6"><EMP_ID>123</EMP_ID><EMP_DEP>8</EMP_DEP><SALARY unit="dollars">5000</SALARY></ROW>
</ROWS>
$$ AS data;

SELECT xmltable.*
  FROM xmldata_sample,
    XMLTABLE('//ROWS/ROW'
      PASSING data
      COLUMNS id int PATH '@id',
        ordinality FOR ORDINALITY,
        "EMP_NAME" text,
        "EMP_ID" text PATH 'EMP_ID',
        SALARY_USD float PATH 'SALARY[@unit = "dollars"]',
        MANAGER_NAME text PATH 'MANAGER_NAME' DEFAULT 'not specified');
```

### Summary mapping

| Description | PostgreSQL | Oracle |
|---|---|---|
| Create table with XML | `CREATE TABLE test (a xml);` | `CREATE TABLE test OF XMLType;` or `CREATE TABLE test (doc XMLType);` |
| Insert XML | `INSERT INTO test VALUES (XMLPARSE (DOCUMENT '...'));` | `INSERT INTO test VALUES ('<?xml ...?>...');` |
| Create index | Index a specific path: `CREATE INDEX test_isbn ON test (((((xpath('/path/tag/text()', a))[1])::text)));` | `CREATE INDEX ... INDEXTYPE IS XDB.XMLIndex PARAMETERS ('PATH TABLE path_tab');` + `DBMS_XMLINDEX.registerParameter(...)` |
| Create fulltext index | `CREATE INDEX my_funcidx ON test USING GIN ( CAST(xpath('/PNAME/text()', a) AS TEXT[]) );` | `CREATE INDEX test_idx ON test (OBJECT_VALUE) INDEXTYPE IS CTXSYS.CONTEXT PARAMETERS('storage pref section group secgroup');` |
| Query using XQuery | Not Supported | `SELECT XMLQuery('for $i in /PurchaseOrder/.../Description where $i[. contains text "Big"] return <Title>{$i}</Title>' PASSING OBJECT_VALUE RETURNING CONTENT) FROM xml_tbl;` |
| Query using XPath | `SELECT xpath('//student/firstname/text()', a) FROM test` | `select sys.XMLType.extract(doc,'/student/firstname/text()') firstname from test;` |
| Check tag exists + cast type | `SELECT XMLCast(XMLQuery('/PurchaseOrder/Reference' PASSING OBJECT_VALUE RETURNING CONTENT) AS VARCHAR2(100)) "REFERENCE" FROM purchaseorder WHERE XMLExists(...);` | `select cast (xpath('//book/title/text()', a) as text[]) as BookTitle from test where xmlexists('//book/title' PASSING by ref a);` |
| Validate schema using XSD | Not out-of-the-box; use a before-insert/delete trigger that finds tags with XPath and casts values to validate | Supported |

## Conversion notes
- Different paradigm/syntax — **application or driver rewrite required**.
- PostgreSQL has **no XQuery support** — rewrite XQuery to XPath (`xpath()`, `xmltable()`).
- PostgreSQL **cannot validate against XSD out-of-the-box** — emulate with triggers that XPath-extract and type-cast values.
- Index XML by indexing a specific path (B-Tree on `xpath(...)::text`, or GIN on `CAST(xpath(...) AS TEXT[])`); queries must use the same path as the index.
- `xmltable()`/`xpath()` may misbehave with non-ASCII data unless server encoding is UTF-8.
