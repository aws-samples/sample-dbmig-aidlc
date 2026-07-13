# Non-portable SQL Server → MySQL constructs (field-tested checklist)

Patterns with no direct Aurora MySQL equivalent and how to convert them, distilled from a real
AdventureWorks `Person` + `Sales` → Aurora MySQL 8.0 run (32 tables, 22 FKs, 4 of 9 views).
Flag, don't silently approximate.

## 1. IDENTITY / AUTO_INCREMENT placement
`int IDENTITY(1,1)` → `int AUTO_INCREMENT`. MySQL requires the AUTO_INCREMENT column to be the
**leading column of some key**. When IDENTITY is the *second* PK column (e.g.
`EmailAddress(BusinessEntityID, EmailAddressID)`, `SalesOrderDetail(SalesOrderID,
SalesOrderDetailID)`), add an extra `KEY(identitycol)`. `migrate-data` reseeds AUTO_INCREMENT
after load.

## 2. Types
- `uniqueidentifier` → `char(36)`; `NEWID()` default → `DEFAULT (UUID())` (MySQL 8 expression
  default needs parentheses). `binary(16)` + `UUID_TO_BIN` is a denser alternative.
- `bit` → `tinyint(1)`; `DEFAULT ((0))` → `DEFAULT 0`.
- `money` → `decimal(19,4)`, `smallmoney` → `decimal(10,4)`, `numeric(p,s)` → `decimal(p,s)`.
- `datetime` → `datetime(3)`; `GETDATE()` default → `DEFAULT CURRENT_TIMESTAMP(3)` (MySQL 8
  allows multiple such columns per table). `datetime2(p)` → `datetime(LEAST(p,6))`.
- `tinyint` is **signed** in MySQL but 0-255 in SQL Server → use `tinyint UNSIGNED`.
- `xml` → `longtext` (or JSON); `geography`/`geometry` → `longblob` (opaque) unless using MySQL
  spatial; `rowversion`/`timestamp` is a binary row-version, NOT a datetime → `binary(8)`.

## 3. Computed / persisted columns
SQL Server computed columns (e.g. `SalesOrderHeader.SalesOrderNumber`/`TotalDue`,
`SalesOrderDetail.LineTotal`, `Customer.AccountNumber`) → migrate as **STORED plain columns**
(load the computed value), or a MySQL `GENERATED ... STORED` column when the expression is
portable (no UDF/system-function dependency). Loading the value keeps the target identical to
the source snapshot.

## 4. Reserved-word / mixed-case identifiers
Fold to lower_case; backtick-quote reserved words (`[Group]` → `` `group` ``). SQL Server is
usually case-insensitive; on Linux MySQL table names are case-sensitive — pick a collation
(e.g. `utf8mb4_0900_ai_ci`) and casing convention to match app expectations.

## 5. Namespaced-XML views (HARD BLOCK)
MySQL's `ExtractValue`/`UpdateXML` use a limited XPath and **do NOT support XML namespaces**.
SQL Server views that shred namespaced XML with `.value()`/`.nodes()` (AdventureWorks
`vPersonDemographics`, `vStoreWithDemographics`, `vAdditionalContactInfo` over the
IndividualSurvey/StoreSurvey namespaces) **cannot** be reproduced — flag/skip. (PostgreSQL can,
via `xpath()` with a namespace array; MySQL cannot.) If needed, re-model the XML as JSON and use
MySQL JSON functions.

## 6. Schema = database; cross-database refs
A SQL Server schema maps to a MySQL **database** (`Person`→`person`, `Sales`→`sales`). Qualify
objects `db.table`; cross-database joins, views, and foreign keys all work with qualified names.
The deferred FK + multi-statement apply (see the framework's MULTI_STATEMENTS support) applies a
table's several `ALTER ... ADD FOREIGN KEY` statements together.

## 7. T-SQL programmable objects
`IDENTITY`→`AUTO_INCREMENT`; `SCOPE_IDENTITY()`/`@@IDENTITY`→`LAST_INSERT_ID()`;
`GETDATE()`→`NOW()`; `ISNULL`→`IFNULL`/`COALESCE`; `LEN`→`CHAR_LENGTH`; `TOP n`→`LIMIT n`;
`+` string concat→`CONCAT()`; `MERGE`→`INSERT ... ON DUPLICATE KEY UPDATE`; `TRY/CATCH`→
`DECLARE ... HANDLER`; `RAISERROR`/`THROW`→`SIGNAL SQLSTATE`. CLR, Service Broker, linked
servers, integrated full-text search, and columnstore have no equivalent — redesign or use AWS
services. Triggers must be created in the table's database (qualify the trigger name).

## 8. FKs to non-migrated schemas
In a partial migration, foreign keys to out-of-scope schemas (e.g.
`SalesOrderHeader → Purchasing.ShipMethod`, `SalesPerson → HumanResources.Employee`,
`* → Production.Product`) are **omitted and flagged**, not enforced. Run `inventory` first — it
reports cross-schema dependencies so you can confirm scope before converting.
