# Oracle XML DB and MySQL XML

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.xmldb.html

**Conversion category:** Assisted (three-star feature compatibility; three-star automation) — different paradigm/syntax requires application or driver rewrite.
**SCT automation:** No automation. SCT action code index: XML.

## Oracle

Oracle XML DB provides native XML support: the `XMLType` data type (accessible from SQL; supports XML Schema, XPath, XQuery, XSLT, DOM) and `XMLIndex` (indexes structured to unstructured XML). XML can be schema-based (validated against an XSD) or non-schema-based.

- **Storage model — Binary XML** (default; post-parse, schema-aware, flexible; supports partial update and streaming). Alternative: object-relational storage (efficient for structured XML with few changes).
- **Indexing** — XML Search Index (full-text, recommend Binary XML + XQuery Full Text); `XMLIndex` with a structured component for fixed structured "islands".
- **Languages** — SQL with SQL/XML functions; XQuery and XSLT.

Create XMLType tables/columns/views and insert XML:

```sql
CREATE TABLE orders OF XMLType;
CREATE DIRECTORY xmldir AS path_to_folder_containing_XML_file;
INSERT INTO orders VALUES (XMLType(BFILENAME('XMLDIR',
  'purOrder.xml'), NLS_CHARSET_ID('AL32UTF8')));

CREATE TABLE xwarehouses (warehouse_id NUMBER, warehouse_spec XMLTYPE);

CREATE VIEW warehouse_view AS
SELECT VALUE(p) AS warehouse_xml FROM xwarehouses p;

INSERT INTO xwarehouses
VALUES(100, '<?xml version="1.0"?>
<PO pono="1"><PNAME>Po_1</PNAME><CUSTNAME>John</CUSTNAME>
<SHIPADDR><STREET>1033, Main Street</STREET><CITY>Sunnyvale</CITY>
<STATE>CA</STATE></SHIPADDR></PO>');
```

XML search index + XQuery query:

```sql
CREATE INDEX po_ctx_idx ON po_binxml(OBJECT_VALUE)
INDEXTYPE IS CTXSYS.CONTEXT
PARAMETERS('storage pref section group secgroup');

SELECT XMLQuery('for $i in /PurchaseOrder/LineItems/LineItem/Description
where $i[.contains text "Big" ftand "Street"] return <Title>{$i}</Title>'
PASSING OBJECT_VALUE RETURNING CONTENT)
FROM po_binxml
WHERE XMLExists('/PurchaseOrder/LineItems/LineItem/Description
  [. contains text "Big" ftand "Street"]');
```

SQL/XML functions:
- `XMLQuery` (SELECT — returns XMLType), `XMLTable` (FROM — shred XML into relational columns), `XMLExists` (WHERE — boolean), `XMLCast` (convert XQuery scalar to NUMBER/VARCHAR2/CLOB/etc.).

```sql
SELECT po.reference, li.*
FROM po_binaryxml p,
XMLTable('/PurchaseOrder' PASSING p.OBJECT_VALUE
COLUMNS reference VARCHAR2(30) PATH 'Reference',
        lineitem XMLType PATH 'LineItems/LineItem') po,
XMLTable('/LineItem' PASSING po.lineitem
COLUMNS itemno NUMBER(38) PATH '@ItemNumber',
        description VARCHAR2(256) PATH 'Description') li;

SELECT OBJECT_VALUE FROM purchaseorder
  WHERE XMLExists('/PurchaseOrder[SpecialInstructions="Expedite"]' PASSING OBJECT_VALUE);
```

## MySQL

Aurora MySQL has minimal XML support (and a strong native JSON type instead). It supports just two XML functions, and there is **no XML data type** — store XML in `VARCHAR`/text columns.

`ExtractValue(xml, xpath)` returns the CDATA of matched children (space-delimited for multiple matches; tags/sub-tags not returned):

```sql
SELECT ExtractValue('<Root><Person>John</Person>
<Person>Jim</Person></Root>','/Root/Person');
-- John Jim
```

`UpdateXML(xml, xpath, new_fragment)` replaces a matched fragment (returns original if zero or multiple matches):

```sql
SELECT UpdateXML('<Root><Person>John</Person>
<Person>Jim</Person></Root>', '/Root','<Person>Jack</Person>');
-- <Person>Jack</Person>
```

Note: Aurora MySQL does **not** support the MySQL `LOAD XML` statement; load XML into regular tables from S3 instead.

## Conversion notes

| Feature | Oracle | Aurora MySQL |
|---|---|---|
| XML functions | `XMLQuery`, `XPath`, `XMLTable`, `XMLExists`, `XMLCast` | `ExtractValue`, `UpdateXML` |
| Create XML table | `CREATE TABLE t OF XMLType;` / `(doc XMLType)` | Not supported — use `VARCHAR`/text |
| Insert XML | Into `XMLType` column | Load into regular tables from S3 |
| Indexing | `XMLIndex` / `CTXSYS.CONTEXT` full-text | Use generated columns + indexes (JSON-style); no XML full-text |
| Query XPath | `XMLType.extract(doc,'/student/firstname/text()')` | `ExtractValue(doc,'//student//firstname')` |
| Query XQuery | `XMLQuery(...)` | N/A |
| Validate XSD | Supported | Not supported |

- Re-architect XML-heavy designs: prefer Aurora MySQL's native JSON type and 25+ JSON functions where possible.
- XPath queries map to `ExtractValue`; updates map to `UpdateXML`; XQuery, XSD validation, and XML full-text indexing have no equivalent.
- Application code/drivers using Oracle SQL/XML must be rewritten.
