# SQL Server graph features for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.graph.html

**Conversion category:** Blocked (One star feature compatibility — feature not supported; requires workaround)
**SCT automation:** No automation

## SQL Server

SQL Server (2017+) offers graph database capabilities to model many-to-many relationships, integrated into T-SQL. A graph is a collection of nodes (entities) and edges (relationships); both can have properties. Distinguishing features: edges are first-class entities with attributes; a single edge can connect multiple nodes; easy pattern matching, multi-hop navigation, transitive closure, and polymorphic queries.

Use a graph database when: data is hierarchical (beyond `HierarchyID` limits, e.g. multiple parents), complex evolving many-to-many relationships, or analysis of interconnected data.

New `CREATE TABLE … AS NODE`/`AS EDGE` syntax and the `MATCH` keyword (ASCII-art pattern matching):

```sql
CREATE TABLE Person (ID INTEGER PRIMARY KEY, Name VARCHAR(100), Age INT) AS NODE;
CREATE TABLE friends (StartDate date) AS EDGE;

-- Find friends of John
SELECT Person2.Name
FROM Person Person1, Friends, Person Person2
WHERE MATCH(Person1-(Friends)->Person2)
AND Person1.Name = 'John';
```

SQL Server 2019 adds cascaded delete actions on edge constraints (enforcing semantics/integrity) and table/index partitioning for graph tables.

## MySQL

Currently, MySQL/Aurora MySQL does **not** provide native graph database features.

## Conversion notes

- No native equivalent in Aurora MySQL — migration requires implementing a workaround.
- Re-model node/edge tables as standard relational tables with junction/association tables for many-to-many relationships.
- Replace `MATCH` pattern-matching / multi-hop navigation with relational joins or recursive queries at the application layer.
- For genuine graph workloads, consider a purpose-built graph database (e.g. Amazon Neptune) instead of forcing the model into Aurora MySQL.
